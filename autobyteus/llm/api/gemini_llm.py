import logging
import asyncio
from typing import Dict, List, AsyncGenerator, Any, Optional
from google.genai import types as genai_types
from autobyteus.llm.models import LLMModel
from autobyteus.llm.base_llm import BaseLLM
from autobyteus.llm.utils.llm_config import LLMConfig
from autobyteus.llm.utils.messages import MessageRole, Message
from autobyteus.llm.utils.token_usage import TokenUsage
from autobyteus.llm.utils.response_types import CompleteResponse, ChunkResponse
from autobyteus.utils.gemini_helper import initialize_gemini_client_with_runtime
from autobyteus.utils.gemini_model_mapping import resolve_model_for_runtime
from autobyteus.llm.converters import convert_gemini_tool_calls
from autobyteus.llm.prompt_renderers.gemini_prompt_renderer import GeminiPromptRenderer

logger = logging.getLogger(__name__)

def _split_gemini_parts(parts: List[Any]) -> tuple[str, str]:
    """Split Gemini content parts into visible text and thought summaries."""
    content_segments: List[str] = []
    thought_segments: List[str] = []
    for part in parts or []:
        text = getattr(part, "text", None)
        if not text:
            continue
        if getattr(part, "thought", False):
            thought_segments.append(text)
        else:
            content_segments.append(text)
    return "".join(content_segments), "".join(thought_segments)


def _split_system_message(messages: List[Message]) -> tuple[Optional[str], List[Message]]:
    system_parts = [msg.content for msg in messages if msg.role == MessageRole.SYSTEM and msg.content]
    system_prompt = "\n".join(system_parts) if system_parts else None
    remaining = [msg for msg in messages if msg.role != MessageRole.SYSTEM]
    return system_prompt, remaining


class GeminiLLM(BaseLLM):
    def __init__(self, model: LLMModel = None, llm_config: LLMConfig = None):
        self.generation_config_dict = {
            "response_mime_type": "text/plain",
        }
        
        if model is None:
            # Default to the latest low-latency Gemini LLM.
            model = LLMModel['gemini-3-flash-preview']
        if llm_config is None:
            llm_config = LLMConfig()
            
        super().__init__(model=model, llm_config=llm_config)
        
        try:
            self.client, self.runtime_info = initialize_gemini_client_with_runtime()
            self.async_client = self.client.aio
            self._renderer = GeminiPromptRenderer()
        except Exception as e:
            # Re-raise or handle initialization errors specifically for the LLM context if needed
            logger.error(f"Failed to initialize Gemini LLM: {str(e)}")
            raise

    def _get_generation_config(self, system_prompt: Optional[str] = None) -> genai_types.GenerateContentConfig:
        """Builds the generation config, handling special cases like 'thinking'."""
        config = self.generation_config_dict.copy()

        # Map thinking_level to token budget
        # Values based on Gemini 3 API recommendations
        THINKING_LEVEL_BUDGETS = {
            "minimal": 0,
            "low": 1024,
            "medium": 4096,
            "high": 16384,
        }
        
        # Read thinking_level from extra_params (set by user config)
        # Default to "minimal" (0 tokens) for backward compatibility
        thinking_level = self.config.extra_params.get("thinking_level", "minimal")
        thinking_budget = THINKING_LEVEL_BUDGETS.get(thinking_level, 0)
        
        include_thoughts = self.config.extra_params.get("include_thoughts", False)
        if not isinstance(include_thoughts, bool):
            include_thoughts = False
        thinking_config = genai_types.ThinkingConfig(
            thinking_budget=thinking_budget,
            include_thoughts=include_thoughts
        )
        
        # System instruction is now part of the config
        system_instruction = system_prompt if system_prompt is not None else self.system_message

        return genai_types.GenerateContentConfig(
            **config,
            thinking_config=thinking_config,
            system_instruction=system_instruction
        )

    async def _send_messages_to_llm(self, messages: List[Message], **kwargs) -> CompleteResponse:
        try:
            system_prompt, non_system = _split_system_message(messages)
            history = await self._renderer.render(non_system)
            generation_config = self._get_generation_config(system_prompt=system_prompt)

            # FIX: Removed 'models/' prefix to support Vertex AI
            runtime_adjusted_model = resolve_model_for_runtime(
                self.model.value,
                modality="llm",
                runtime=getattr(self, "runtime_info", None) and self.runtime_info.runtime,
            )
            response = await self.async_client.models.generate_content(
                model=runtime_adjusted_model,
                contents=history,
                config=generation_config,
            )
            
            assistant_message = response.text or ""
            reasoning_summary = None
            if response.candidates and response.candidates[0].content and response.candidates[0].content.parts:
                parsed_text, parsed_thoughts = _split_gemini_parts(response.candidates[0].content.parts)
                if parsed_text:
                    assistant_message = parsed_text
                if parsed_thoughts:
                    reasoning_summary = parsed_thoughts

            token_usage = TokenUsage(
                prompt_tokens=0,
                completion_tokens=0,
                total_tokens=0
            )
            
            return CompleteResponse(
                content=assistant_message,
                reasoning=reasoning_summary,
                usage=token_usage
            )
        except Exception as e:
            logger.error(f"Error in Gemini API call: {str(e)}")
            raise ValueError(f"Error in Gemini API call: {str(e)}")
    
    async def _stream_messages_to_llm(self, messages: List[Message], **kwargs) -> AsyncGenerator[ChunkResponse, None]:
        complete_response = ""
        complete_reasoning = ""
        
        # Extract tools if provided
        tools = kwargs.get("tools")
        
        try:
            system_prompt, non_system = _split_system_message(messages)
            history = await self._renderer.render(non_system)
            generation_config = self._get_generation_config(system_prompt=system_prompt)
            
            # Add tools to config if present
            # Note: In google.genai, tools can be passed in config
            if tools:
                # Auto-wrap tools if they appear to be raw function declarations
                if isinstance(tools, list) and len(tools) > 0:
                    first_tool = tools[0]
                    # Check if it's a raw declaration (dict with name/description) but NOT a wrapper (dict with function_declarations)
                    if isinstance(first_tool, dict):
                        is_declaration = "name" in first_tool and "description" in first_tool
                        is_wrapper = "function_declarations" in first_tool
                        
                        if is_declaration and not is_wrapper:
                             # Wrap the list of declarations into a single Tool structure
                             tools = [{"function_declarations": tools}]

                try:
                    generation_config.tools = tools
                except Exception:
                    # Fallback or strict strict typing issues
                    pass

            # FIX: Removed 'models/' prefix to support Vertex AI
            runtime_adjusted_model = resolve_model_for_runtime(
                self.model.value,
                modality="llm",
                runtime=getattr(self, "runtime_info", None) and self.runtime_info.runtime,
            )
            
            # Prepare call args
            call_kwargs = {
                "model": runtime_adjusted_model,
                "contents": history,
                "config": generation_config,
            }
            # If explicit tools argument is needed and not supported in config for this SDK version:
            # call_kwargs['tools'] = tools 
            # But usually config holds it.

            response_stream = await self.async_client.models.generate_content_stream(**call_kwargs)

            async for chunk in response_stream:
                handled_parts = False
                if chunk.candidates and chunk.candidates[0].content and chunk.candidates[0].content.parts:
                    handled_parts = True
                    for part in chunk.candidates[0].content.parts:
                        part_text = getattr(part, "text", None)
                        if part_text:
                            if getattr(part, "thought", False):
                                complete_reasoning += part_text
                                yield ChunkResponse(
                                    content="",
                                    reasoning=part_text,
                                    is_complete=False
                                )
                            else:
                                complete_response += part_text
                                yield ChunkResponse(
                                    content=part_text,
                                    is_complete=False
                                )

                        tool_calls = convert_gemini_tool_calls(part)
                        if tool_calls:
                            yield ChunkResponse(
                                content="",
                                tool_calls=tool_calls,
                                is_complete=False
                            )

                if not handled_parts:
                    chunk_text = chunk.text
                    if chunk_text:
                        complete_response += chunk_text
                        yield ChunkResponse(
                            content=chunk_text,
                            is_complete=False
                        )

            token_usage = TokenUsage(
                prompt_tokens=0,
                completion_tokens=0,
                total_tokens=0
            )

            yield ChunkResponse(
                content="",
                is_complete=True,
                usage=token_usage
            )
        except Exception as e:
            logger.error(f"Error in Gemini API streaming call: {str(e)}")
            raise ValueError(f"Error in Gemini API streaming call: {str(e)}")

    async def cleanup(self):
        await super().cleanup()
