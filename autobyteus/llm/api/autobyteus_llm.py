from typing import Dict, Optional, List, AsyncGenerator
from autobyteus.llm.base_llm import BaseLLM
from autobyteus.llm.models import LLMModel
from autobyteus.llm.utils.llm_config import LLMConfig
from autobyteus.llm.utils.token_usage import TokenUsage
from autobyteus.llm.utils.response_types import CompleteResponse, ChunkResponse
from autobyteus.llm.utils.messages import Message
from autobyteus.clients import AutobyteusClient
from autobyteus.llm.prompt_renderers.autobyteus_prompt_renderer import AutobyteusPromptRenderer
import logging
import uuid

logger = logging.getLogger(__name__)

class AutobyteusLLM(BaseLLM):
    def __init__(self, model: LLMModel, llm_config: LLMConfig):
        if not model.host_url:
            raise ValueError("AutobyteusLLM requires a host_url to be set in its LLMModel object.")

        super().__init__(model=model, llm_config=llm_config)
        
        self.client = AutobyteusClient(server_url=self.model.host_url)
        self.conversation_id = str(uuid.uuid4())
        self._renderer = AutobyteusPromptRenderer()
        logger.info(f"AutobyteusLLM initialized for model '{self.model.model_identifier}' with conversation ID: {self.conversation_id}")

    async def _send_messages_to_llm(
        self,
        messages: List[Message],
        **kwargs
    ) -> CompleteResponse:
        rendered = await self._renderer.render(messages)
        if not rendered:
            raise ValueError("AutobyteusLLM requires at least one user message.")
        payload = rendered[0]
        try:
            response = await self.client.send_message(
                conversation_id=self.conversation_id,
                model_name=self.model.name,
                user_message=payload.get("content", ""),
                image_urls=payload.get("image_urls", []),
                audio_urls=payload.get("audio_urls", []),
                video_urls=payload.get("video_urls", []),
            )
            
            assistant_message = (
                response.get("response")
                or response.get("content")
                or response.get("message")
                or ""
            )
            
            token_usage_data = response.get('token_usage') or {}
            token_usage = TokenUsage(
                prompt_tokens=token_usage_data.get('prompt_tokens', 0),
                completion_tokens=token_usage_data.get('completion_tokens', 0),
                total_tokens=token_usage_data.get('total_tokens', 0)
            )
            
            return CompleteResponse(
                content=assistant_message,
                usage=token_usage
            )
        except Exception as e:
            logger.error(f"Error processing message: {str(e)}")
            raise

    async def _stream_messages_to_llm(
        self,
        messages: List[Message],
        **kwargs
    ) -> AsyncGenerator[ChunkResponse, None]:
        rendered = await self._renderer.render(messages)
        if not rendered:
            raise ValueError("AutobyteusLLM requires at least one user message.")
        payload = rendered[0]
        complete_response = ""
        
        try:
            async for chunk in self.client.stream_message(
                conversation_id=self.conversation_id,
                model_name=self.model.name,
                user_message=payload.get("content", ""),
                image_urls=payload.get("image_urls", []),
                audio_urls=payload.get("audio_urls", []),
                video_urls=payload.get("video_urls", []),
            ):
                if 'error' in chunk:
                    raise RuntimeError(chunk['error'])
                
                content = chunk.get('content', '')
                if content:
                    complete_response += content

                is_complete = chunk.get('is_complete', False)
                token_usage = None
                if is_complete:
                    token_usage_data = chunk.get('token_usage') or {}
                    token_usage = TokenUsage(
                        prompt_tokens=token_usage_data.get('prompt_tokens', 0),
                        completion_tokens=token_usage_data.get('completion_tokens', 0),
                        total_tokens=token_usage_data.get('total_tokens', 0)
                    )

                yield ChunkResponse(
                    content=content,
                    reasoning=chunk.get('reasoning'),
                    is_complete=is_complete,
                    image_urls=chunk.get('image_urls', []),
                    audio_urls=chunk.get('audio_urls', []),
                    video_urls=chunk.get('video_urls', []),
                    usage=token_usage
                )
        except Exception as e:
            logger.error(f"Error streaming message: {str(e)}")
            raise

    async def cleanup(self):
        """
        Clean up the remote conversation. The owning agent controls the HTTP
        client lifecycle.
        """
        try:
            await self.client.cleanup(self.conversation_id)
            await super().cleanup()
        except Exception as e:
            logger.error(f"Error during cleanup: {str(e)}")
