from typing import Dict, Optional, List
import os
from enum import Enum
from autobyteus.llm.models import LLMModel
from autobyteus.llm.base_llm import BaseLLM
from dotenv import load_dotenv
from mistralai import Mistral, UserMessage, AssistantMessage

load_dotenv()

class MessageRole(Enum):
    USER = "user"
    ASSISTANT = "assistant"

class Message:
    def __init__(self, role: MessageRole, content: str):
        self.role = role
        self.content = content

    def to_mistral_message(self):
        if self.role == MessageRole.USER:
            return UserMessage(content=self.content)
        elif self.role == MessageRole.ASSISTANT:
            return AssistantMessage(content=self.content)

class MistralChat(BaseLLM):
    def __init__(self, model_name: LLMModel = None):
        self.client = self.initialize()
        self.model = model_name.value if model_name else "mistral-large-latest"
        self.messages = []
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
