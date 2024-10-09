from typing import Dict, List
import openai
from dotenv import load_dotenv
import os
from enum import Enum
from autobyteus.llm.models import LLMModel

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

class OpenAIChat:
    def __init__(self, model_name: LLMModel.OpenaiApiModels = None, system_message: str = None):
        self.initialize()
        self.model = model_name.value if model_name else LLMModel.OpenaiApiModels.GPT_3_5_TURBO_API.value
        self.messages = []
        if system_message:
            self.messages.append(Message(MessageRole.SYSTEM, system_message))

    @classmethod
    def initialize(cls):
        load_dotenv()
        openai.api_key = os.getenv("OPENAI_API_KEY")

    def send_message(self, user_message: str, **kwargs) -> str:
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