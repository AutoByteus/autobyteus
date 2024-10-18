from typing import Dict
from enum import Enum

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

    def to_mistral_message(self):
        if self.role == MessageRole.USER:
            from mistralai import UserMessage
            return UserMessage(content=self.content)
        elif self.role == MessageRole.ASSISTANT:
            from mistralai import AssistantMessage
            return AssistantMessage(content=self.content)