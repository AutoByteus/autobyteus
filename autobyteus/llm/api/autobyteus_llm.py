from typing import Dict, Optional, List, AsyncGenerator
from autobyteus.llm.base_llm import BaseLLM
from autobyteus.llm.models import LLMModel
from autobyteus.llm.utils.llm_config import LLMConfig
from autobyteus.llm.utils.token_usage import TokenUsage
from autobyteus.llm.utils.response_types import CompleteResponse, ChunkResponse
from autobyteus.llm.user_message import LLMUserMessage
from autobyteus_llm_client.client import AutobyteusClient
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
        logger.info(f"AutobyteusLLM initialized for model '{self.model.model_identifier}' with conversation ID: {self.conversation_id}")

    async def _send_user_message_to_llm(
        self,
        user_message: LLMUserMessage,
        **kwargs
    ) -> CompleteResponse:
        self.add_user_message(user_message)
        try:
            response = await self.client.send_message(
                conversation_id=self.conversation_id,
                model_name=self.model.name,
                user_message=user_message.content,
                image_urls=user_message.image_urls,
                audio_urls=user_message.audio_urls,
                video_urls=user_message.video_urls
            )
            
            assistant_message = response['response']
            self.add_assistant_message(assistant_message)
            
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
            await self._handle_error_cleanup()
            raise

    async def _stream_user_message_to_llm(
        self,
        user_message: LLMUserMessage,
        **kwargs
    ) -> AsyncGenerator[ChunkResponse, None]:
        self.add_user_message(user_message)
        complete_response = ""
        
        try:
            async for chunk in self.client.stream_message(
                conversation_id=self.conversation_id,
                model_name=self.model.name,
                user_message=user_message.content,
                image_urls=user_message.image_urls,
                audio_urls=user_message.audio_urls,
                video_urls=user_message.video_urls
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
            
            self.add_assistant_message(complete_response)
        except Exception as e:
            logger.error(f"Error streaming message: {str(e)}")
            await self._handle_error_cleanup()
            raise

    async def cleanup(self):
        try:
            await self.client.cleanup(self.conversation_id)
            await super().cleanup()
        except Exception as e:
            logger.error(f"Error during cleanup: {str(e)}")
        finally:
            await self.client.close()

    async def _handle_error_cleanup(self):
        try:
            await self.cleanup()
        except Exception as cleanup_error:
            logger.error(f"Error during error cleanup: {str(cleanup_error)}")
