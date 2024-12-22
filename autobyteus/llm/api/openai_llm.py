import logging
from typing import Optional, List, AsyncGenerator
import openai
import os
from autobyteus.llm.models import LLMModel
from autobyteus.llm.base_llm import BaseLLM
from autobyteus.llm.utils.messages import MessageRole, Message
from autobyteus.llm.utils.process_image import process_image

logger = logging.getLogger(__name__)


class OpenAILLM(BaseLLM):
    def __init__(self, model_name: LLMModel = None, system_message: str = None):
        self.initialize()

        # Initialize base with model configuration
        super().__init__(model=model_name or LLMModel.GPT_3_5_TURBO_API)

        self.messages = []
        if system_message:
            self.messages.append(Message(MessageRole.SYSTEM, system_message))

        # super().__init__(model=self.config.to_dict())
        logger.info(f"OpenAILLM initialized with model: {self.config.model}")

    @classmethod
    def initialize(cls):
        openai_api_key = os.getenv("OPENAI_API_KEY")
        if not openai_api_key:
            logger.error("OPENAI_API_KEY environment variable is not set.")
            raise ValueError("OPENAI_API_KEY environment variable is not set.")
        openai.api_key = openai_api_key
        logger.info("OpenAI API key set successfully")

    async def _send_user_message_to_llm(
        self, user_message: str, file_paths: Optional[List[str]] = None, **kwargs
    ) -> str:
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

        self.messages.append(Message(MessageRole.USER, content))
        logger.debug(f"Prepared message content: {content}")

        try:
            logger.info("Sending request to OpenAI API")

            completion_params = self.config.to_dict()
            completion_params["messages"] = [msg.to_dict() for msg in self.messages]

            response = openai.chat.completions.create(**completion_params)
            assistant_message = response.choices[0].message.content
            self.messages.append(Message(MessageRole.ASSISTANT, assistant_message))
            logger.info("Received response from OpenAI API")
            return assistant_message
        except Exception as e:
            logger.error(f"Error in OpenAI API request: {str(e)}")
            raise ValueError(f"Error in OpenAI API request: {str(e)}")

    async def _stream_user_message_to_llm(
        self, user_message: str, file_paths: Optional[List[str]] = None, **kwargs
    ) -> AsyncGenerator[str, None]:
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
                    logger.error(
                        f"Error processing image for streaming {file_path}: {str(e)}"
                    )
                    continue

        self.messages.append(Message(MessageRole.USER, content))
        logger.debug(f"Prepared streaming message content: {content}")

        complete_response = ""

        try:
            logger.info("Starting streaming request to OpenAI API")
            stream = openai.chat.completions.create(
                model=self.model,
                messages=[msg.to_dict() for msg in self.messages],
                max_tokens=self.max_tokens,
                stream=True,
            )

            for chunk in stream:
                if chunk.choices[0].delta.content is not None:
                    token = chunk.choices[0].delta.content
                    complete_response += token
                    yield token

            self.messages.append(Message(MessageRole.ASSISTANT, complete_response))
            logger.info("Completed streaming response from OpenAI API")

        except Exception as e:
            logger.error(f"Error in OpenAI API streaming: {str(e)}")
            raise ValueError(f"Error in OpenAI API streaming: {str(e)}")

    async def cleanup(self):
        logger.info("Cleanup completed for OpenAILLM")
        pass
