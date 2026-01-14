import logging
import base64
import asyncio
import mimetypes
from typing import Dict, List, AsyncGenerator, Any
from google.genai import types as genai_types
from autobyteus.llm.models import LLMModel
from autobyteus.llm.base_llm import BaseLLM
from autobyteus.llm.utils.llm_config import LLMConfig
from autobyteus.llm.utils.messages import MessageRole, Message
from autobyteus.llm.utils.token_usage import TokenUsage
from autobyteus.llm.utils.response_types import CompleteResponse, ChunkResponse
from autobyteus.llm.user_message import LLMUserMessage
from autobyteus.utils.gemini_helper import initialize_gemini_client_with_runtime
from autobyteus.utils.gemini_model_mapping import resolve_model_for_runtime
from autobyteus.llm.converters import convert_gemini_tool_calls
from autobyteus.llm.utils.media_payload_formatter import media_source_to_base64, get_mime_type

logger = logging.getLogger(__name__)

async def _format_gemini_history(messages: List[Message]) -> List[Dict[str, Any]]:
    """Formats internal message history for the Gemini API."""
    history = []
    # System message is handled separately in the new API
    for msg in messages:
        if msg.role in [MessageRole.USER, MessageRole.ASSISTANT]:
            role = 'model' if msg.role == MessageRole.ASSISTANT else 'user'
            parts = []
            
            # Text content
            if msg.content:
                parts.append({"text": msg.content})
            
            # Process media (Images, Audio, Video)
            # Currently leveraging media_source_to_base64 which handles local images and URLs.
            # TODO: Add dedicated support for Audio/Video local file reading if strict validation is needed,
            # though URLs usually work if supported by the fetcher.
            media_urls = msg.image_urls + msg.audio_urls + msg.video_urls
            
            for url in media_urls:
                try:
                    # Fetch/Read data as base64
                    b64_data = await media_source_to_base64(url)
                    # Decode to bytes for Gemini SDK
                    data_bytes = base64.b64decode(b64_data)
                    
                    # Determine MIME type
                    mime_type, _ = mimetypes.guess_type(url)
                    if not mime_type:
                        # Default fallback
                        mime_type = get_mime_type(url)
                    
                    parts.append(genai_types.Part.from_bytes(data=data_bytes, mime_type=mime_type))
                except Exception as e:
                    logger.error(f"Failed to process media content {url}: {e}")
            
            if parts:
                history.append({"role": role, "parts": parts})
    return history

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
        except Exception as e:
            # Re-raise or handle initialization errors specifically for the LLM context if needed
            logger.error(f"Failed to initialize Gemini LLM: {str(e)}")
            raise

    def _get_generation_config(self) -> genai_types.GenerateContentConfig:
        """Builds the generation config, handling special cases like 'thinking'."""
        config = self.generation_config_dict.copy()

        thinking_config = None
        if "flash" in self.model.value:
            thinking_config = genai_types.ThinkingConfig(thinking_budget=0)
        
        # System instruction is now part of the config
        system_instruction = self.system_message if self.system_message else None
        
        return genai_types.GenerateContentConfig(
            **config,
            thinking_config=thinking_config,
            system_instruction=system_instruction
        )

    async def _send_user_message_to_llm(self, user_message: LLMUserMessage, **kwargs) -> CompleteResponse:
        self.add_user_message(user_message)
        
        try:
            history = await _format_gemini_history(self.messages)
            generation_config = self._get_generation_config()

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
            
            assistant_message = response.text
            self.add_assistant_message(assistant_message)
            
            token_usage = TokenUsage(
                prompt_tokens=0,
                completion_tokens=0,
                total_tokens=0
            )
            
            return CompleteResponse(
                content=assistant_message,
                usage=token_usage
            )
        except Exception as e:
            logger.error(f"Error in Gemini API call: {str(e)}")
            raise ValueError(f"Error in Gemini API call: {str(e)}")
    
    async def _stream_user_message_to_llm(self, user_message: LLMUserMessage, **kwargs) -> AsyncGenerator[ChunkResponse, None]:
        self.add_user_message(user_message)
        complete_response = ""
        
        # Extract tools if provided
        tools = kwargs.get("tools")
        
        try:
            history = await _format_gemini_history(self.messages)
            generation_config = self._get_generation_config()
            
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
                chunk_text = chunk.text
                if chunk_text:
                    complete_response += chunk_text
                    yield ChunkResponse(
                        content=chunk_text,
                        is_complete=False
                    )
                
                # Handle tool calls
                # Iterate parts in the candidate
                if chunk.candidates and chunk.candidates[0].content and chunk.candidates[0].content.parts:
                    for part in chunk.candidates[0].content.parts:
                        tool_calls = convert_gemini_tool_calls(part)
                        if tool_calls:
                            yield ChunkResponse(
                                content="",
                                tool_calls=tool_calls,
                                is_complete=False
                            )

            self.add_assistant_message(complete_response)

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
