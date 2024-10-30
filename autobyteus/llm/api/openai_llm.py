from typing import Optional, List
import openai
import os
from autobyteus.llm.models import LLMModel
from autobyteus.llm.base_llm import BaseLLM
from autobyteus.llm.utils.messages import MessageRole, Message

class OpenAILLM(BaseLLM):
    def __init__(self, model_name: LLMModel = None, system_message: str = None):
        self.initialize()
        self.model = model_name.value if model_name else LLMModel.GPT_3_5_TURBO_API.value
        self.messages = []
        if system_message:
            self.messages.append(Message(MessageRole.SYSTEM, system_message))
        super().__init__(model=self.model, tokenizer_model_name="gpt-3.5-turbo")

    @classmethod
    def initialize(cls):
        openai_api_key = os.getenv("OPENAI_API_KEY")
        if not openai_api_key:
            raise ValueError(
                "OPENAI_API_KEY environment variable is not set. "
                "Please set this variable in your environment."
            )
        openai.api_key = openai_api_key

    async def _send_user_message_to_llm(self, user_message: str, file_paths: Optional[List[str]] = None, **kwargs) -> str:
        self.messages.append(Message(MessageRole.USER, user_message))

        try:
            response = openai.chat.completions.create(
                model=self.model,
                messages=[msg.to_dict() for msg in self.messages]
            )

            assistant_message = response.choices[0].message.content
            self.messages.append(Message(MessageRole.ASSISTANT, assistant_message))
            return assistant_message
        except (AttributeError, IndexError) as e:
            raise ValueError(f"Unexpected structure in OpenAI API response: {str(e)}")

    async def cleanup(self):
        pass