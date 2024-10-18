# base_chat.py
from enum import Enum
from typing import Dict
from autobyteus.llm.base_llm import BaseLLM
from autobyteus.llm.utils.llm_config import LLMConfig

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

class BaseChatAPI(BaseLLM):
    def __init__(self, model_name=None, system_message: str = None, custom_config: LLMConfig = None):
        super().__init__(model_name, custom_config)
        self.client = self.initialize()
        self.model = model_name.value if model_name else self.default_model
        self.messages = []
        if system_message:
            self.messages.append(Message(MessageRole.SYSTEM, system_message))

    @classmethod
    def initialize(cls):
        raise NotImplementedError