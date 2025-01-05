
from typing import Dict, Optional, List, AsyncGenerator
import os
import logging
from autobyteus.llm.models import LLMModel
from autobyteus.llm.base_llm import BaseLLM
from mistralai import Mistral
from autobyteus.llm.utils.messages import MessageRole, Message
from autobyteus.llm.utils.llm_config import LLMConfig
from autobyteus.llm.utils.token_usage import TokenUsage
from autobyteus.llm.utils.response_types import CompleteResponse, ChunkResponse

# Configure logger
logger = logging.getLogger(__name__)

class MistralLLM(BaseLLM):
    def __init__(self, model: LLMModel = None, custom_config: LLMConfig = None):
        super().__init__(model=model or LLMModel.MISTRAL_LARGE_API, system_message=None, custom_config=custom_config)
        self.client = self.initialize()
        logger.info(f"MistralLLM initialized with model: {self.model}")

    @classmethod
    def initialize(cls):
        mistral_api_key = os.environ.get("MISTRAL_API_KEY")
        if not mistral_api_key:
            logger.error("MISTRAL_API_KEY environment variable is not set")
            raise ValueError(
                "MISTRAL_API_KEY environment variable is not set. "
                "Please set this variable in your environment."
            )
        try:
            return Mistral(api_key=mistral_api_key)
        except Exception as e:
            logger.error(f"Failed to initialize Mistral client: {str(e)}")
            raise ValueError(f"Failed to initialize Mistral client: {str(e)}")

    def _create_token_usage(self, usage_data: Dict) -> TokenUsage:
        """Convert Mistral usage data to TokenUsage format."""
        return TokenUsage(
            prompt_tokens=usage_data.prompt_tokens,
            completion_tokens=usage_data.completion_tokens,
            total_tokens=usage_data.total_tokens
        )

    async def _send_user_message_to_llm(
        self, user_message: str, file_paths: Optional[List[str]] = None, **kwargs
    ) -> CompleteResponse:
        self.add_user_message(user_message)

        try:
            mistral_messages = [msg.to_mistral_message() for msg in self.messages]
            
            chat_response = self.client.chat.complete(
                model=self.model.value,
                messages=mistral_messages,
            )

            assistant_message = chat_response.choices[0].message.content
            self.add_assistant_message(assistant_message)

            # Create token usage if available
            token_usage = None
            if hasattr(chat_response, 'usage') and chat_response.usage:
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
        self, user_message: str, file_paths: Optional[List[str]] = None, **kwargs
    ) -> AsyncGenerator[ChunkResponse, None]:
        self.add_user_message(user_message)
        
        try:
            mistral_messages = [msg.to_mistral_message() for msg in self.messages]
            
            stream = await self.client.chat.stream_async(
                model=self.model.value,
                messages=mistral_messages,
            )

            accumulated_message = ""
            
            async for chunk in stream:
                if chunk.data.choices[0].delta.content is not None:
                    token = chunk.data.choices[0].delta.content
                    accumulated_message += token
                    
                    # For intermediate chunks, yield without usage
                    yield ChunkResponse(
                        content=token,
                        is_complete=False
                    )

                # Check if this is the last chunk with usage data
                if hasattr(chunk.data, 'usage') and chunk.data.usage is not None:
                    token_usage = self._create_token_usage(chunk.data.usage)
                    yield ChunkResponse(
                        content="",
                        is_complete=True,
                        usage=token_usage
                    )

            # After streaming is complete, store the full message
            self.add_assistant_message(accumulated_message)
        except Exception as e:
            logger.error(f"Error in Mistral API streaming call: {str(e)}")
            raise ValueError(f"Error in Mistral API streaming call: {str(e)}")
    
    async def cleanup(self):
        # Clean up any resources if needed
        logger.debug("Cleaning up MistralLLM instance")
        self.messages = []
        super().cleanup()
