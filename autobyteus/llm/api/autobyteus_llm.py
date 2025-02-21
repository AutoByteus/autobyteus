from typing import Dict, Optional, List, AsyncGenerator
from autobyteus.llm.base_llm import BaseLLM
from autobyteus.llm.models import LLMModel
from autobyteus.llm.utils.llm_config import LLMConfig
from autobyteus.llm.utils.token_usage import TokenUsage
from autobyteus.llm.utils.response_types import CompleteResponse, ChunkResponse
from autobyteus_llm_client.client import AutobyteusClient
import logging
import uuid

logger = logging.getLogger(__name__)

class AutobyteusLLM(BaseLLM):
    def __init__(
        self,
        model: LLMModel = None,
        system_message: str = None,
        custom_config: LLMConfig = None
    ):
        super().__init__(
            model=model,
            system_message=system_message,
            custom_config=custom_config
        )
        self.client = AutobyteusClient()
        self.conversation_id = str(uuid.uuid4())
        logger.info(f"AutobyteusLLM initialized with model: {self.model} and conversation ID: {self.conversation_id}")

    async def _send_user_message_to_llm(
        self,
        user_message: str,
        file_paths: Optional[List[str]] = None,
        **kwargs
    ) -> CompleteResponse:
        user_message_index = kwargs.get("user_message_index")
        if user_message_index is None:
            raise ValueError("user_message_index is required in kwargs")

        self.add_user_message(user_message)
        try:
            response = await self.client.send_message(
                conversation_id=self.conversation_id,
                model_name=self.model.name,
                user_message=user_message,
                file_paths=file_paths,
                user_message_index=user_message_index
            )
            
            assistant_message = response['response']
            self.add_assistant_message(assistant_message)
            
            token_usage_data = response.get('token_usage', {})
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
        user_message: str,
        file_paths: Optional[List[str]] = None,
        **kwargs
    ) -> AsyncGenerator[ChunkResponse, None]:
        user_message_index = kwargs.get("user_message_index")
        if user_message_index is None:
            raise ValueError("user_message_index is required in kwargs")

        self.add_user_message(user_message)
        complete_response = ""
        
        try:
            async for chunk in self.client.stream_message(
                conversation_id=self.conversation_id,
                model_name=self.model.name,
                user_message=user_message,
                file_paths=file_paths,
                user_message_index=user_message_index
            ):
                if 'error' in chunk:
                    raise RuntimeError(chunk['error'])
                
                content = chunk.get('content', '')
                complete_response += content
                is_complete = chunk.get('is_complete', False)
                
                # If this is the final chunk, include token usage
                if is_complete:
                    token_usage = None
                    if chunk.get('token_usage'):
                        token_usage = TokenUsage(
                            prompt_tokens=chunk['token_usage'].get('prompt_tokens', 0),
                            completion_tokens=chunk['token_usage'].get('completion_tokens', 0),
                            total_tokens=chunk['token_usage'].get('total_tokens', 0)
                        )
                    yield ChunkResponse(
                        content=content,
                        is_complete=True,
                        usage=token_usage
                    )
                else:
                    yield ChunkResponse(
                        content=content,
                        is_complete=False
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
        """Handle cleanup operations after errors"""
        try:
            await self.cleanup()
        except Exception as cleanup_error:
            logger.error(f"Error during error cleanup: {str(cleanup_error)}")
