from typing import Dict, Optional, List
from mistralai.client import MistralClient
import os
from enum import Enum
from autobyteus.llm.models import LLMModel
from autobyteus.llm.base_llm import BaseLLM
from dotenv import load_dotenv

load_dotenv()

class MessageRole(Enum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"

class Message:
    def __init__(self, role: MessageRole, content: str):
        self.role = role
        self.content = content

    def to_dict(self) -> Dict[str, str]:
        return {"role": self.role.value, "content": self.content}

class MistralChat(BaseLLM):
    def __init__(self, model_name: LLMModel = None, system_message: str = None):
        self.client = self.initialize()
        self.model = model_name.value if model_name else "mistral-large-latest"
        self.messages = []
        if system_message:
            self.messages.append(Message(MessageRole.SYSTEM, system_message))
        super().__init__(model=self.model)

    @classmethod
    def initialize(cls):
        mistral_api_key = os.environ.get("MISTRAL_API_KEY")
        if not mistral_api_key:
            raise ValueError(
                "MISTRAL_API_KEY environment variable is not set. "
                "Please set this variable in your .env file or export it in your shell."
            )
        try:
            return MistralClient(api_key=mistral_api_key)
        except Exception as e:
            raise ValueError(f"Failed to initialize Mistral client: {str(e)}")

    async def _send_user_message_to_llm(self, user_message: str, file_paths: Optional[List[str]] = None, **kwargs) -> str:
        self.messages.append(Message(MessageRole.USER, user_message))
        try:
            chat_response = self.client.chat.complete(
                model=self.model,
                messages=[msg.to_dict() for msg in self.messages]
            )
            assistant_message = chat_response.choices[0].message.content
            self.messages.append(Message(MessageRole.ASSISTANT, assistant_message))
            return assistant_message
        except Exception as e:
            raise ValueError(f"Error in Mistral API call: {str(e)}")

    async def cleanup(self):
        pass