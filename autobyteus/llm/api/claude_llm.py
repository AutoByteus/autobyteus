import asyncio
import anthropic
import os
import logging
from typing import Dict, Optional, List, AsyncGenerator, Tuple, Any

from autobyteus.llm.models import LLMModel
from autobyteus.llm.base_llm import BaseLLM
from autobyteus.llm.utils.llm_config import LLMConfig
from autobyteus.llm.utils.messages import MessageRole, Message
from autobyteus.llm.utils.token_usage import TokenUsage
from autobyteus.llm.utils.response_types import CompleteResponse, ChunkResponse
from autobyteus.llm.user_message import LLMUserMessage
from autobyteus.llm.converters import convert_anthropic_tool_call
from autobyteus.llm.utils.media_payload_formatter import (
    media_source_to_base64,
    get_mime_type,
    is_valid_media_path
)

logger = logging.getLogger(__name__)

def _build_thinking_param(extra_params: Dict) -> Optional[Dict]:
    enabled = extra_params.get("thinking_enabled", False)
    if not isinstance(enabled, bool) or not enabled:
        return None

    budget = extra_params.get("thinking_budget_tokens", 1024)
    try:
        budget_int = int(budget)
    except (TypeError, ValueError):
        budget_int = 1024

    return {"type": "enabled", "budget_tokens": budget_int}


def _split_claude_content_blocks(blocks: List) -> Tuple[str, str]:
    """Split Claude content blocks into visible text and thinking summaries."""
    content_segments: List[str] = []
    thinking_segments: List[str] = []

    for block in blocks or []:
        block_type = getattr(block, "type", None)
        if block_type is None and isinstance(block, dict):
            block_type = block.get("type")

        if block_type == "text":
            text = getattr(block, "text", None)
            if text is None and isinstance(block, dict):
                text = block.get("text")
            if text:
                content_segments.append(text)
        elif block_type == "thinking":
            thinking = getattr(block, "thinking", None)
            if thinking is None and isinstance(block, dict):
                thinking = block.get("thinking")
            if thinking:
                thinking_segments.append(thinking)
        elif block_type == "redacted_thinking":
            redacted = getattr(block, "redacted_thinking", None)
            if redacted is None and isinstance(block, dict):
                redacted = block.get("redacted_thinking")
            if redacted:
                thinking_segments.append(redacted)

    return "".join(content_segments), "".join(thinking_segments)

class ClaudeLLM(BaseLLM):
    def __init__(self, model: LLMModel = None, llm_config: LLMConfig = None):
        if model is None:
            model = LLMModel['claude-4.5-sonnet']
        if llm_config is None:
            llm_config = LLMConfig()
            
        super().__init__(model=model, llm_config=llm_config)
        self.client = self.initialize()
        # Claude Sonnet 4.5 currently allows up to ~8k output tokens; let config override.
        self.max_tokens = llm_config.max_tokens if llm_config.max_tokens is not None else 8192
    
    @classmethod
    def initialize(cls):
        anthropic_api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not anthropic_api_key:
            raise ValueError(
                "ANTHROPIC_API_KEY environment variable is not set. "
                "Please set this variable in your environment."
            )
        try:
            return anthropic.Anthropic(api_key=anthropic_api_key)
        except Exception as e:
            raise ValueError(f"Failed to initialize Anthropic client: {str(e)}")
    
    async def _format_anthropic_messages(self) -> List[Dict]:
        """
        Convert internal Message objects into the shape expected by
        Anthropic's messages API, handling both text and images.
        """
        formatted_messages: List[Dict] = []
        valid_image_mimes = {'image/jpeg', 'image/png', 'image/gif', 'image/webp'}

        for msg in self.messages:
            if msg.role == MessageRole.SYSTEM:
                continue
            
            # Check for images in the message
            if msg.image_urls:
                content_blocks: List[Dict[str, Any]] = []
                
                # Process images
                image_tasks = [media_source_to_base64(url) for url in msg.image_urls]
                try:
                    base64_images = await asyncio.gather(*image_tasks)
                    
                    for i, b64_data in enumerate(base64_images):
                        original_url = msg.image_urls[i]
                        # Determine MIME type
                        mime_type = get_mime_type(original_url)
                        
                        # Validate MIME type 
                        if mime_type not in valid_image_mimes:
                            logger.warning(
                                f"Unsupported image MIME type '{mime_type}' for {original_url}. "
                                f"Anthropic supports: {valid_image_mimes}. Defaulting to image/jpeg."
                            )
                            mime_type = "image/jpeg"

                        content_blocks.append({
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": mime_type,
                                "data": b64_data
                            }
                        })
                except Exception as e:
                    logger.error(f"Error processing images for Claude: {e}")
                    # Continue without images if processing fails, or maybe raise?
                    # For now, let's log and proceed, potentially with just text.
                
                # Add text content if present
                if msg.content:
                    content_blocks.append({
                        "type": "text",
                        "text": msg.content
                    })
                    
                formatted_messages.append({
                    "role": msg.role.value,
                    "content": content_blocks
                })

            else:
                # Text-only message
                formatted_messages.append(
                    {
                        "role": msg.role.value,
                        "content": msg.content or "",
                    }
                )

        return formatted_messages
    
    def _create_token_usage(self, input_tokens: int, output_tokens: int) -> TokenUsage:
        return TokenUsage(
            prompt_tokens=input_tokens,
            completion_tokens=output_tokens,
            total_tokens=input_tokens + output_tokens
        )
    
    async def _send_user_message_to_llm(self, user_message: LLMUserMessage, **kwargs) -> CompleteResponse:
        self.add_user_message(user_message)

        try:
            # Prepare formatted messages (images + text)
            formatted_messages = await self._format_anthropic_messages()
            thinking_param = _build_thinking_param(self.config.extra_params)

            request_kwargs = {
                "model": self.model.value,
                "max_tokens": self.max_tokens,
                "system": self.system_message,
                "messages": formatted_messages,
            }
            if thinking_param:
                # Extended thinking is not compatible with temperature modifications
                request_kwargs["thinking"] = thinking_param
            else:
                request_kwargs["temperature"] = 0

            response = self.client.messages.create(
                **request_kwargs
            )

            assistant_message = getattr(response, "text", "") or ""
            reasoning_summary = None
            if response.content:
                parsed_text, parsed_thinking = _split_claude_content_blocks(response.content)
                if parsed_text:
                    assistant_message = parsed_text
                if parsed_thinking:
                    reasoning_summary = parsed_thinking

            self.add_assistant_message(assistant_message, reasoning_content=reasoning_summary)

            token_usage = self._create_token_usage(
                response.usage.input_tokens,
                response.usage.output_tokens
            )
            
            logger.info(f"Token usage - Input: {response.usage.input_tokens}, Output: {response.usage.output_tokens}")
            
            return CompleteResponse(
                content=assistant_message,
                reasoning=reasoning_summary,
                usage=token_usage
            )
        except anthropic.APIError as e:
            logger.error(f"Error in Claude API call: {str(e)}")
            raise ValueError(f"Error in Claude API call: {str(e)}")
    
    async def _stream_user_message_to_llm(
        self, user_message: LLMUserMessage, **kwargs
    ) -> AsyncGenerator[ChunkResponse, None]:
        self.add_user_message(user_message)
        complete_response = ""
        complete_reasoning = ""
        final_message = None

        # Extract tools if provided
        tools = kwargs.get("tools")

        try:
            # Prepare arguments for stream
            formatted_messages = await self._format_anthropic_messages()
            thinking_param = _build_thinking_param(self.config.extra_params)
            stream_kwargs = {
                "model": self.model.value,
                "max_tokens": self.max_tokens,
                "system": self.system_message,
                "messages": formatted_messages,
            }
            if thinking_param:
                # Extended thinking is not compatible with temperature modifications
                stream_kwargs["thinking"] = thinking_param
            else:
                stream_kwargs["temperature"] = 0
            
            if tools:
                stream_kwargs["tools"] = tools

            with self.client.messages.stream(**stream_kwargs) as stream:
                for event in stream:
                    # DEBUG: Log all events from Anthropic stream
                    print(f"[ClaudeLLM DEBUG] Event type: {event.type}")
                    if hasattr(event, 'delta'):
                        delta_type = getattr(event.delta, 'type', None)
                        print(f"[ClaudeLLM DEBUG]   Delta type: {delta_type}")
                        if delta_type == 'input_json_delta':
                            partial_json = getattr(event.delta, 'partial_json', None)
                            print(f"[ClaudeLLM DEBUG]   Partial JSON: {partial_json!r}")
                    if hasattr(event, 'content_block'):
                        print(f"[ClaudeLLM DEBUG]   Content block: {event.content_block}")
                    
                    # Handle text content
                    if event.type == "content_block_delta":
                        delta_type = getattr(event.delta, "type", None)
                        if delta_type == "text_delta":
                            complete_response += event.delta.text
                            yield ChunkResponse(
                                content=event.delta.text,
                                is_complete=False
                            )
                        elif delta_type == "thinking_delta":
                            thinking_delta = getattr(event.delta, "thinking", None)
                            if thinking_delta:
                                complete_reasoning += thinking_delta
                                yield ChunkResponse(
                                    content="",
                                    reasoning=thinking_delta,
                                    is_complete=False
                                )
                    
                    # Handle tool calls using common converter
                    tool_calls = convert_anthropic_tool_call(event)
                    if tool_calls:
                        print(f"[ClaudeLLM DEBUG] Tool calls converted: {tool_calls}")
                        for tc in tool_calls:
                            print(f"[ClaudeLLM DEBUG]   Tool call: name={tc.name}, call_id={tc.call_id}, args_delta={tc.arguments_delta!r}")
                        yield ChunkResponse(
                            content="",
                            tool_calls=tool_calls,
                            is_complete=False
                        )
                    
                final_message = stream.get_final_message()
                if final_message:
                    token_usage = self._create_token_usage(
                        final_message.usage.input_tokens,
                        final_message.usage.output_tokens
                    )
                    logger.info(f"Final token usage - Input: {final_message.usage.input_tokens}, "
                               f"Output: {final_message.usage.output_tokens}")
                    yield ChunkResponse(
                        content="",
                        is_complete=True,
                        usage=token_usage
                    )

            # Only add assistant message if there's actual content.
            # Tool-call-only responses should not add empty messages, as Claude API
            # rejects subsequent requests with "all messages must have non-empty content".
            if complete_response:
                self.add_assistant_message(complete_response, reasoning_content=complete_reasoning or None)
        except anthropic.APIError as e:
            logger.error(f"Error in Claude API streaming: {str(e)}")
            raise ValueError(f"Error in Claude API streaming: {str(e)}")
    
    async def cleanup(self):
        await super().cleanup()
