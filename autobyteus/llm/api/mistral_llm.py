from typing import Dict, Optional, List, AsyncGenerator
import os
from autobyteus.llm.models import LLMModel
from autobyteus.llm.base_llm import BaseLLM
from mistralai import Mistral
from autobyteus.llm.utils.messages import MessageRole, Message
from autobyteus.llm.utils.llm_config import LLMConfig
from autobyteus.llm.utils.process_image import process_image
import logging

logger = logging.getLogger(__name__)


class MistralLLM(BaseLLM):
    def __init__(self, model_name: LLMModel = None, custom_config: LLMConfig = None):
        self.client = self.initialize()

        # Initialize base with model configuration
        super().__init__(model=model_name or LLMModel.MISTRAL_LARGE_API)
        self.messages = []

        logger.info(f"MistralLLM initialized with model: {self.config.model}")

    @classmethod
    def initialize(cls):
        mistral_api_key = os.environ.get("MISTRAL_API_KEY")
        if not mistral_api_key:
            raise ValueError(
                "MISTRAL_API_KEY environment variable is not set. "
                "Please set this variable in your environment."
            )
        try:
            return Mistral(api_key=mistral_api_key)
        except Exception as e:
            raise ValueError(f"Failed to initialize Mistral client: {str(e)}")

    async def _send_user_message_to_llm(
        self, user_message: str, file_paths: Optional[List[str]] = None, **kwargs
    ) -> str:
        ## paramters from singelton config
        completion_params = self.config.to_dict()

        # If we only have text and no images, send directly
        if not file_paths:
            self.messages.append(Message(MessageRole.USER, user_message))

        else:
            # Handle mixed content with images
            content = []

            if user_message:
                content.append({"type": "text", "content": user_message})

            for file_path in file_paths:
                try:
                    image_content = process_image(
                        file_path
                    )  ## processing images as per Model APIs requirements
                    content.append(image_content)
                    logger.info(f"Processed image: {file_path}")

                except ValueError as e:
                    logger.error(f"Error processing image {file_path}: {str(e)}")
                    continue

            self.messages.append(Message(MessageRole.USER, content))

        logger.debug(f"Prepared message: {self.messages[-1].content}")

        try:
            mistral_messages = [msg.to_mistral_message() for msg in self.messages]
            completion_params["messages"] = mistral_messages

            chat_response = self.client.chat.complete(**completion_params)

            assistant_message = chat_response.choices[0].message.content
            self.messages.append(Message(MessageRole.ASSISTANT, assistant_message))
            return assistant_message

        except Exception as e:
            raise ValueError(f"Error in Mistral API call: {str(e)}")

    async def _stream_user_message_to_llm(
        self, user_message: str, file_paths: Optional[List[str]] = None, **kwargs
    ) -> AsyncGenerator[str, None]:
        """
        Stream responses from Mistral API token by token using async streaming.
        """
        completion_params = self.config.to_dict()

        # Handle multimodal content
        if not file_paths:
            self.messages.append(Message(MessageRole.USER, user_message))

        else:
            content = []

            if user_message:
                content.append({"type": "text", "content": user_message})

            for file_path in file_paths:
                try:
                    image_content = process_image(file_path)
                    content.append(image_content)
                    logger.info(f"Processed image: {file_path}")

                except ValueError as e:
                    logger.error(f"Error processing image {file_path}: {str(e)}")
                    continue

            self.messages.append(Message(MessageRole.USER, content))

        try:
            mistral_messages = [msg.to_mistral_message() for msg in self.messages]
            completion_params["messages"] = mistral_messages

            # Await the stream_async call
            stream = await self.client.chat.stream_async(**completion_params)

            accumulated_message = ""

            async for chunk in stream:
                if chunk.data.choices[0].delta.content is not None:
                    token = chunk.data.choices[0].delta.content
                    accumulated_message += token
                    yield token

            # After streaming is complete, store the full message
            self.messages.append(Message(MessageRole.ASSISTANT, accumulated_message))

        except Exception as e:
            raise ValueError(f"Error in Mistral API streaming call: {str(e)}")

    async def cleanup(self):
        # Clean up any resources if needed
        self.messages = []
