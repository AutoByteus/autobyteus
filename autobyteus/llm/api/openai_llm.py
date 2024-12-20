from typing import Optional, List, AsyncGenerator
import openai
import os
from autobyteus.llm.models import LLMModel
from autobyteus.llm.base_llm import BaseLLM
from autobyteus.llm.utils.messages import MessageRole, Message
from autobyteus.llm.utils.process_image import process_image


class OpenAILLM(BaseLLM):
    def __init__(self, model_name: LLMModel = None, system_message: str = None):
        self.initialize()
        self.model = (
            model_name.value if model_name else LLMModel.GPT_3_5_TURBO_API.value
        )
        self.max_tokens = 8000  # Adding max_tokens to match Claude implementation
        self.messages = []

        ## Add system message to the message history
        if system_message:
            self.messages.append(Message(MessageRole.SYSTEM, system_message))

        super().__init__(model=self.model)

    @classmethod
    def initialize(cls):
        openai_api_key = os.getenv("OPENAI_API_KEY")
        if not openai_api_key:
            raise ValueError(
                "OPENAI_API_KEY environment variable is not set. "
                "Please set this variable in your environment."
            )
        openai.api_key = openai_api_key

    async def _send_user_message_to_llm(
        self, user_message: str, file_paths: Optional[List[str]] = None, **kwargs
    ) -> str:
        content = []

        if user_message:
            content.append({"type": "text", "text": user_message})

        if file_paths:
            for file_path in file_paths:
                try:
                    image_content = process_image(file_path)  ## process images
                    content.append(image_content)
                except ValueError:
                    continue

        # Create message with structured content
        self.messages.append(Message(MessageRole.USER, content))

        try:
            response = openai.chat.completions.create(
                model=self.model,
                messages=[msg.to_dict() for msg in self.messages],
                max_tokens=self.max_tokens,
            )
            assistant_message = response.choices[0].message.content
            self.messages.append(Message(MessageRole.ASSISTANT, assistant_message))
            return assistant_message
        except (AttributeError, IndexError) as e:
            raise ValueError(f"Unexpected structure in OpenAI API response: {str(e)}")

    async def _stream_user_message_to_llm(
        self, user_message: str, file_paths: Optional[List[str]] = None, **kwargs
    ) -> AsyncGenerator[str, None]:
        content = []

        if user_message:
            content.append({"type": "text", "text": user_message})

        if file_paths:
            for file_path in file_paths:
                try:
                    image_content = process_image(file_path)  ## process images
                    content.append(image_content)
                except ValueError:
                    continue

        self.messages.append(Message(MessageRole.USER, user_message))

        complete_response = ""

        try:
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

            # After streaming is complete, update message history
            self.messages.append(Message(MessageRole.ASSISTANT, complete_response))

        except Exception as e:
            raise ValueError(f"Error in OpenAI API streaming: {str(e)}")

    async def cleanup(self):
        pass
