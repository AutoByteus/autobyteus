
import logging
from typing import Optional, List, AsyncGenerator
import openai
from openai.types.completion_usage import CompletionUsage
from openai.types.chat import ChatCompletionChunk
import os
from autobyteus.llm.models import LLMModel
from autobyteus.llm.base_llm import BaseLLM
from autobyteus.llm.utils.messages import MessageRole, Message
from autobyteus.llm.utils.image_payload_formatter import process_image
from autobyteus.llm.utils.token_usage import TokenUsage
from autobyteus.llm.utils.response_types import CompleteResponse, ChunkResponse

logger = logging.getLogger(__name__)

class OpenAILLM(BaseLLM):
    def __init__(self, model: LLMModel = None, system_message: str = None):
        super().__init__(model=model or LLMModel.GPT_3_5_TURBO_API, system_message=system_message)
        self.initialize()
        self.max_tokens = 8000
        logger.info(f"OpenAILLM initialized with model: {self.model}")
    
    @classmethod
    def initialize(cls):
        openai_api_key = os.getenv("OPENAI_API_KEY")
        if not openai_api_key:
            logger.error("OPENAI_API_KEY environment variable is not set.")
            raise ValueError("OPENAI_API_KEY environment variable is not set.")
        openai.api_key = openai_api_key
        logger.info("OpenAI API key set successfully")
    
    def _create_token_usage(self, usage_data: Optional[CompletionUsage]) -> Optional[TokenUsage]:
        """Convert OpenAI usage data to TokenUsage format."""
        if not usage_data:
            return None
        
        return TokenUsage(
            prompt_tokens=usage_data.prompt_tokens,
            completion_tokens=usage_data.completion_tokens,
            total_tokens=usage_data.total_tokens
        )
    
    async def _send_user_message_to_llm(
        self, user_message: str, file_paths: Optional[List[str]] = None, **kwargs
    ) -> CompleteResponse:
        content = []

        if user_message:
            content.append({"type": "text", "text": user_message})

        if file_paths:
            for file_path in file_paths:
                try:
                    image_content = process_image(file_path)
                    content.append(image_content)
                    logger.info(f"Processed image: {file_path}")
                except ValueError as e:
                    logger.error(f"Error processing image {file_path}: {str(e)}")
                    continue

        self.add_user_message(content)
        logger.debug(f"Prepared message content: {content}")

        try:
            logger.info("Sending request to OpenAI API")
            response = openai.chat.completions.create(
                model=self.model.value,
                messages=[msg.to_dict() for msg in self.messages],
                max_tokens=self.max_tokens,
            )
            assistant_message = response.choices[0].message.content
            self.add_assistant_message(assistant_message)
            
            token_usage = self._create_token_usage(response.usage)
            logger.info("Received response from OpenAI API with usage data")
            
            return CompleteResponse(
                content=assistant_message,
                usage=token_usage
            )
        except Exception as e:
            logger.error(f"Error in OpenAI API request: {str(e)}")
            raise ValueError(f"Error in OpenAI API request: {str(e)}")
    
    async def _stream_user_message_to_llm(
        self, user_message: str, file_paths: Optional[List[str]] = None, **kwargs
    ) -> AsyncGenerator[ChunkResponse, None]:
        content = []

        if user_message:
            content.append({"type": "text", "text": user_message})

        if file_paths:
            for file_path in file_paths:
                try:
                    image_content = process_image(file_path)
                    content.append(image_content)
                    logger.info(f"Processed image for streaming: {file_path}")
                except ValueError as e:
                    logger.error(f"Error processing image for streaming {file_path}: {str(e)}")
                    continue

        self.add_user_message(content)
        logger.debug(f"Prepared streaming message content: {content}")

        complete_response = ""

        try:
            logger.info("Starting streaming request to OpenAI API")
            stream = openai.chat.completions.create(
                model=self.model.value,
                messages=[msg.to_dict() for msg in self.messages],
                max_tokens=self.max_tokens,
                stream=True,
                stream_options={"include_usage": True}  # Added this option to get usage stats
            )

            async for chunk in stream:
                chunk: ChatCompletionChunk
                if chunk.choices[0].delta.content is not None:
                    token = chunk.choices[0].delta.content
                    complete_response += token
                    
                    # For intermediate chunks, don't include usage
                    yield ChunkResponse(
                        content=token,
                        is_complete=False
                    )

                # Check if this is the last chunk (it will have usage data)
                if hasattr(chunk, 'usage') and chunk.usage is not None:
                    token_usage = self._create_token_usage(chunk.usage)
                    yield ChunkResponse(
                        content="",
                        is_complete=True,
                        usage=token_usage
                    )

            self.add_assistant_message(complete_response)
            logger.info("Completed streaming response from OpenAI API")
        except Exception as e:
            logger.error(f"Error in OpenAI API streaming: {str(e)}")
            raise ValueError(f"Error in OpenAI API streaming: {str(e)}")
    
    async def cleanup(self):
        super().cleanup()
