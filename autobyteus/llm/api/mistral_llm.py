from typing import Dict, Optional, List, Any, AsyncGenerator, Union
import os
import logging
import httpx
import asyncio
from autobyteus.llm.models import LLMModel
from autobyteus.llm.base_llm import BaseLLM
from mistralai import Mistral
from autobyteus.llm.utils.messages import Message, MessageRole
from autobyteus.llm.utils.llm_config import LLMConfig
from autobyteus.llm.utils.token_usage import TokenUsage
from autobyteus.llm.utils.response_types import CompleteResponse, ChunkResponse
from autobyteus.llm.user_message import LLMUserMessage
from autobyteus.llm.utils.media_payload_formatter import image_source_to_base64, get_mime_type, is_valid_image_path

logger = logging.getLogger(__name__)

async def _format_mistral_messages(messages: List[Message]) -> List[Dict[str, Any]]:
    """Formats a list of internal Message objects into a list of dictionaries for the Mistral API."""
    mistral_messages = []
    for msg in messages:
        # Skip empty messages from non-system roles as Mistral API may reject them
        if not msg.content and not msg.image_urls and msg.role != MessageRole.SYSTEM:
            continue

        content: Union[str, List[Dict[str, Any]]]

        if msg.image_urls:
            content_parts: List[Dict[str, Any]] = []
            if msg.content:
                content_parts.append({"type": "text", "text": msg.content})

            image_tasks = [image_source_to_base64(url) for url in msg.image_urls]
            try:
                base64_images = await asyncio.gather(*image_tasks)
                for i, b64_image in enumerate(base64_images):
                    original_url = msg.image_urls[i]
                    mime_type = get_mime_type(original_url) if is_valid_image_path(original_url) else "image/jpeg"
                    data_uri = f"data:{mime_type};base64,{b64_image}"
                    
                    # Mistral's format for image parts
                    content_parts.append({
                        "type": "image_url",
                        "image_url": {
                            "url": data_uri
                        }
                    })
            except Exception as e:
                logger.error(f"Error processing images for Mistral: {e}")
            
            if msg.audio_urls:
                logger.warning("MistralLLM does not yet support audio; skipping.")
            if msg.video_urls:
                logger.warning("MistralLLM does not yet support video; skipping.")
            
            content = content_parts
        else:
            content = msg.content or ""
        
        mistral_messages.append({"role": msg.role.value, "content": content})
            
    return mistral_messages


class MistralLLM(BaseLLM):
    def __init__(self, model: LLMModel = None, llm_config: LLMConfig = None):
        if model is None:
            model = LLMModel['mistral-large']
        if llm_config is None:
            llm_config = LLMConfig()
            
        super().__init__(model=model, llm_config=llm_config)
        self.http_client = httpx.AsyncClient()
        self.client: Mistral = self._initialize()
        logger.info(f"MistralLLM initialized with model: {self.model}")

    def _initialize(self) -> Mistral:
        mistral_api_key = os.environ.get("MISTRAL_API_KEY")
        if not mistral_api_key:
            logger.error("MISTRAL_API_KEY environment variable is not set")
            raise ValueError("MISTRAL_API_KEY environment variable is not set.")
        try:
            return Mistral(api_key=mistral_api_key, client=self.http_client)
        except Exception as e:
            logger.error(f"Failed to initialize Mistral client: {str(e)}")
            raise ValueError(f"Failed to initialize Mistral client: {str(e)}")

    def _create_token_usage(self, usage_data: Any) -> TokenUsage:
        """Convert Mistral usage data to TokenUsage format."""
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
            mistral_messages = await _format_mistral_messages(self.messages)
            
            chat_response = await self.client.chat.complete_async(
                model=self.model.value,
                messages=mistral_messages,
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens,
                top_p=self.config.top_p,
            )

            assistant_message = chat_response.choices[0].message.content
            self.add_assistant_message(assistant_message)

            token_usage = self._create_token_usage(chat_response.usage)
            logger.debug(f"Token usage recorded: {token_usage}")

            return CompleteResponse(
                content=assistant_message,
                usage=token_usage
            )
        except Exception as e:
            logger.error(f"Error in Mistral API call: {str(e)}")
            raise ValueError(f"Error in Mistral API call: {str(e)}")
    
    async def _stream_user_message_to_llm(
        self, user_message: LLMUserMessage, **kwargs
    ) -> AsyncGenerator[ChunkResponse, None]:
        self.add_user_message(user_message)
        
        accumulated_message = ""
        final_usage = None
        
        try:
            mistral_messages = await _format_mistral_messages(self.messages)

            stream = self.client.chat.stream_async(
                model=self.model.value,
                messages=mistral_messages,
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens,
                top_p=self.config.top_p,
            )

            async for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content is not None:
                    token = chunk.choices[0].delta.content
                    accumulated_message += token
                    
                    yield ChunkResponse(content=token, is_complete=False)

                if hasattr(chunk, 'usage') and chunk.usage:
                    final_usage = self._create_token_usage(chunk.usage)

            # Yield the final chunk with usage data
            yield ChunkResponse(
                content="",
                is_complete=True,
                usage=final_usage
            )
            
            self.add_assistant_message(accumulated_message)
        except Exception as e:
            logger.error(f"Error in Mistral API streaming call: {str(e)}")
            raise ValueError(f"Error in Mistral API streaming call: {str(e)}")
    
    async def cleanup(self):
        logger.debug("Cleaning up MistralLLM instance")
        if self.http_client and not self.http_client.is_closed:
            await self.http_client.aclose()
        await super().cleanup()
