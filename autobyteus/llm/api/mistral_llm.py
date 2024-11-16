from typing import Optional, List
import os
from autobyteus.llm.models import LLMModel
from autobyteus.llm.base_llm import BaseLLM
from mistralai import Mistral
from autobyteus.llm.utils.messages import MessageRole, Message
from autobyteus.llm.utils.llm_config import LLMConfig  # Assuming LLMConfig is needed

class MistralLLM(BaseLLM):
    def __init__(self, model_name: LLMModel = None, custom_config: LLMConfig = None):
        self.client = self.initialize()
        self.model = model_name.value if model_name else "mistral-large-latest"
        self.messages = []
        super().__init__(model=self.model, custom_config=custom_config)

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

    async def _send_user_message_to_llm(self, user_message: str, file_paths: Optional[List[str]] = None, **kwargs) -> str:
        self.messages.append(Message(MessageRole.USER, user_message))

        try:
            mistral_messages = [msg.to_mistral_message() for msg in self.messages]
            
            chat_response = self.client.chat.complete(
                model=self.model,
                messages=mistral_messages,
            )

            assistant_message = chat_response.choices[0].message.content
            self.messages.append(Message(MessageRole.ASSISTANT, assistant_message))
            return assistant_message
        except Exception as e:
            raise ValueError(f"Error in Mistral API call: {str(e)}")

    async def cleanup(self):
        pass