
import logging
import os
from typing import Optional, List, AsyncGenerator
from openai import OpenAI
from autobyteus.llm.base_llm import BaseLLM
from autobyteus.llm.models import LLMModel
from autobyteus.llm.utils.messages import MessageRole, Message
from autobyteus.llm.utils.image_payload_formatter import process_image

logger = logging.getLogger(__name__)

class DeepSeekLLM(BaseLLM):
    def __init__(self, model_name: LLMModel = None, system_message: str = None):
        deepseek_api_key = os.getenv("DEEPSEEK_API_KEY")
        if not deepseek_api_key:
            logger.error("DEEPSEEK_API_KEY environment variable is not set.")
            raise ValueError("DEEPSEEK_API_KEY environment variable is not set.")

        self.client = OpenAI(api_key=deepseek_api_key, base_url="https://api.deepseek.com")
        logger.info("DeepSeek API key and base URL set successfully")

        self.model = model_name.value if model_name else "deepseek-chat"
        self.max_tokens = 8000
        self.messages = []

        if system_message:
            self.messages.append(Message(MessageRole.SYSTEM, system_message))

        super().__init__(model=self.model)
        logger.info(f"DeepSeekLLM initialized with model: {self.model}")

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
            logger.info("Sending request to DeepSeek API")
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[msg.to_dict() for msg in self.messages],
                max_tokens=self.max_tokens,
            )
            assistant_message = response.choices[0].message.content
            self.messages.append(Message(MessageRole.ASSISTANT, assistant_message))
            logger.info("Received response from DeepSeek API")
            return assistant_message
        except Exception as e:
            logger.error(f"Error in DeepSeek API request: {str(e)}")
            raise ValueError(f"Error in DeepSeek API request: {str(e)}")

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
                    logger.error(f"Error processing image for streaming {file_path}: {str(e)}")
                    continue

        self.messages.append(Message(MessageRole.USER, content))
        logger.debug(f"Prepared streaming message content: {content}")

        complete_response = ""

        try:
            logger.info("Starting streaming request to DeepSeek API")
            stream = self.client.chat.completions.create(
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
            logger.info("Completed streaming response from DeepSeek API")

        except Exception as e:
            logger.error(f"Error in DeepSeek API streaming: {str(e)}")
            raise ValueError(f"Error in DeepSeek API streaming: {str(e)}")

    async def cleanup(self):
        logger.info("Cleanup completed for DeepSeekLLM")
        pass
