import logging
import os
from abc import ABC
from typing import Optional, List, AsyncGenerator, Dict, Any
from openai import OpenAI
from openai.types.completion_usage import CompletionUsage
from openai.types.chat import ChatCompletionChunk
import asyncio

from autobyteus.llm.base_llm import BaseLLM
from autobyteus.llm.models import LLMModel
from autobyteus.llm.utils.llm_config import LLMConfig
from autobyteus.llm.utils.media_payload_formatter import image_source_to_base64, create_data_uri, get_mime_type, is_valid_image_path
from autobyteus.llm.utils.token_usage import TokenUsage
from autobyteus.llm.utils.response_types import CompleteResponse, ChunkResponse
from autobyteus.llm.user_message import LLMUserMessage
from autobyteus.llm.utils.messages import Message

logger = logging.getLogger(__name__)

async def _format_openai_history(messages: List[Message]) -> List[Dict[str, Any]]:
    """A local async function to format history for the OpenAI SDK, handling image processing."""
    formatted_messages = []
    for msg in messages:
        # For multimodal messages, build the content list of parts
        if msg.image_urls or msg.audio_urls or msg.video_urls:
            content_parts: List[Dict[str, Any]] = []
            if msg.content:
                content_parts.append({"type": "text", "text": msg.content})

            image_tasks = []
            if msg.image_urls:
                for url in msg.image_urls:
                    # Create an async task for each image to process them concurrently
                    image_tasks.append(image_source_to_base64(url))
            
            try:
                base64_images = await asyncio.gather(*image_tasks)
                for i, b64_image in enumerate(base64_images):
                    original_url = msg.image_urls[i]
                    # Determine mime type from original path if possible, otherwise default
                    mime_type = get_mime_type(original_url) if is_valid_image_path(original_url) else "image/jpeg"
                    content_parts.append(create_data_uri(mime_type, b64_image))
            except Exception as e:
                logger.error(f"Error processing one or more images: {e}")

            # Placeholder for future audio/video processing
            if msg.audio_urls:
                logger.warning("OpenAI compatible layer does not yet support audio; skipping.")
            if msg.video_urls:
                logger.warning("OpenAI compatible layer does not yet support video; skipping.")

            formatted_messages.append({"role": msg.role.value, "content": content_parts})
        else:
            # For text-only messages, use the simple string format
            formatted_messages.append({"role": msg.role.value, "content": msg.content})
    return formatted_messages


class OpenAICompatibleLLM(BaseLLM, ABC):
    def __init__(
        self,
        model: LLMModel,
        llm_config: LLMConfig,
        api_key_env_var: str,
        base_url: str,
        api_key_default: Optional[str] = None
    ):
        api_key = os.getenv(api_key_env_var)
        if not api_key:
            if api_key_default:
                api_key = api_key_default
                logger.info(f"{api_key_env_var} not set, using default key.")
            else:
                logger.error(f"{api_key_env_var} environment variable is not set.")
                raise ValueError(f"{api_key_env_var} environment variable is not set.")

        self.client = OpenAI(api_key=api_key, base_url=base_url)
        logger.info(f"Initialized OpenAI compatible client with base_url: {base_url}")
        
        super().__init__(model=model, llm_config=llm_config)
        self.max_tokens = 8000

    def _create_token_usage(self, usage_data: Optional[CompletionUsage]) -> Optional[TokenUsage]:
        if not usage_data:
            return None
        return TokenUsage(
            prompt_tokens=usage_data.prompt_tokens,
            completion_tokens=usage_data.completion_tokens,
            total_tokens=usage_data.total_tokens
        )

    async def _send_user_message_to_llm(
        self, user_message: LLMUserMessage, **kwargs
    ) -> CompleteResponse:
        self.add_user_message(user_message)
        
        try:
            formatted_messages = await _format_openai_history(self.messages)
            logger.info(f"Sending request to {self.model.provider.value} API")
            
            params: Dict[str, Any] = {
                "model": self.model.value,
                "messages": formatted_messages,
            }

            if self.config.uses_max_completion_tokens:
                params["max_completion_tokens"] = self.max_tokens
            else:
                params["max_tokens"] = self.max_tokens

            response = self.client.chat.completions.create(**params)
            full_message = response.choices[0].message

            # --- PRESERVED ORIGINAL LOGIC ---
            reasoning = None
            if hasattr(full_message, "reasoning_content") and full_message.reasoning_content:
                reasoning = full_message.reasoning_content
            elif "reasoning_content" in full_message and full_message["reasoning_content"]:
                reasoning = full_message["reasoning_content"]

            main_content = ""
            if hasattr(full_message, "content") and full_message.content:
                main_content = full_message.content
            elif "content" in full_message and full_message["content"]:
                main_content = full_message["content"]
            # --- END PRESERVED LOGIC ---

            self.add_assistant_message(main_content, reasoning_content=reasoning)

            token_usage = self._create_token_usage(response.usage)
            logger.info(f"Received response from {self.model.provider.value} API with usage data")
            
            return CompleteResponse(
                content=main_content,
                reasoning=reasoning,
                usage=token_usage
            )
        except Exception as e:
            logger.error(f"Error in {self.model.provider.value} API request: {str(e)}")
            raise ValueError(f"Error in {self.model.provider.value} API request: {str(e)}")

    async def _stream_user_message_to_llm(
        self, user_message: LLMUserMessage, **kwargs
    ) -> AsyncGenerator[ChunkResponse, None]:
        self.add_user_message(user_message)

        accumulated_reasoning = ""
        accumulated_content = ""

        try:
            formatted_messages = await _format_openai_history(self.messages)
            logger.info(f"Starting streaming request to {self.model.provider.value} API")
            
            params: Dict[str, Any] = {
                "model": self.model.value,
                "messages": formatted_messages,
                "stream": True,
                "stream_options": {"include_usage": True},
            }

            if self.config.uses_max_completion_tokens:
                params["max_completion_tokens"] = self.max_tokens
            else:
                params["max_tokens"] = self.max_tokens

            stream = self.client.chat.completions.create(**params)

            for chunk in stream:
                chunk: ChatCompletionChunk
                if not chunk.choices:
                    continue
                
                delta = chunk.choices[0].delta

                # --- PRESERVED ORIGINAL LOGIC (adapted for streaming) ---
                reasoning_chunk = None
                if hasattr(delta, "reasoning_content") and delta.reasoning_content:
                    reasoning_chunk = delta.reasoning_content
                elif isinstance(delta, dict) and "reasoning_content" in delta and delta["reasoning_content"]:
                    reasoning_chunk = delta["reasoning_content"]
                
                if reasoning_chunk:
                    accumulated_reasoning += reasoning_chunk
                    yield ChunkResponse(content="", reasoning=reasoning_chunk)
                # --- END PRESERVED LOGIC ---

                main_token = delta.content
                if main_token:
                    accumulated_content += main_token
                    yield ChunkResponse(content=main_token, reasoning=None)

                if hasattr(chunk, "usage") and chunk.usage is not None:
                    token_usage = self._create_token_usage(chunk.usage)
                    yield ChunkResponse(
                        content="",
                        reasoning=None,
                        is_complete=True,
                        usage=token_usage
                    )
            
            self.add_assistant_message(accumulated_content, reasoning_content=accumulated_reasoning)
            logger.info(f"Completed streaming response from {self.model.provider.value} API")

        except Exception as e:
            logger.error(f"Error in {self.model.provider.value} API streaming: {str(e)}")
            raise ValueError(f"Error in {self.model.provider.value} API streaming: {str(e)}")

    async def cleanup(self):
        await super().cleanup()
