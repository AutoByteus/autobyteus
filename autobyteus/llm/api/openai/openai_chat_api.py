from typing import Dict, Optional, List
import openai
import os
from enum import Enum
from autobyteus.llm.models import LLMModel
from autobyteus.llm.base_llm import BaseLLM
from dotenv import load_dotenv

load_dotenv()
#load the environment variables in autobyteus-server/app.py
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

class OpenAIChat(BaseLLM):
    def __init__(self, model_name: LLMModel = None, system_message: str = None):
        self.initialize()
        self.model = model_name.value if model_name else LLMModel.GPT_3_5_TURBO_API.value
        self.messages = []
        if system_message:
            self.messages.append(Message(MessageRole.SYSTEM, system_message))
        super().__init__(model=self.model)

    @classmethod
    def initialize(cls):
        openai.api_key = os.getenv("OPENAI_API_KEY")

    async def _send_user_message_to_llm(self, user_message: str, file_paths: Optional[List[str]] = None, **kwargs) -> str:
        self.messages.append(Message(MessageRole.USER, user_message))

        response = openai.chat.completions.create(
            model=self.model,
            messages=[msg.to_dict() for msg in self.messages]
        )

        try:
            assistant_message = response.choices[0].message.content
            self.messages.append(Message(MessageRole.ASSISTANT, assistant_message))
            return assistant_message
        except (AttributeError, IndexError) as e:
            raise ValueError(f"Unexpected structure in OpenAI API response: {str(e)}")

    async def cleanup(self):
        pass