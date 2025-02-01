from typing import Dict, Union, List, Optional
from enum import Enum

class MessageRole(Enum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"

class Message:
    def __init__(self, role: MessageRole, content: Union[str, List[Dict]], reasoning_content: Optional[str] = None):
        """
        Initializes a Message.
        
        Args:
            role (MessageRole): The role of the message.
            content (Union[str, List[Dict]]): The content of the message.
            reasoning_content (Optional[str]): Optional reasoning content for reasoning models.
        """
        self.role = role
        self.content = content
        self.reasoning_content = reasoning_content  # Optional field for reasoning content

    def to_dict(self) -> Dict[str, Union[str, None]]:
        result = {"role": self.role.value, "content": self.content}
        if self.reasoning_content is not None:
            result["reasoning_content"] = self.reasoning_content
        return result

    def to_mistral_message(self):
        if self.role == MessageRole.USER:
            from mistralai import UserMessage
            return UserMessage(content=self.content)
        elif self.role == MessageRole.ASSISTANT:
            from mistralai import AssistantMessage
            return AssistantMessage(content=self.content)
        elif self.role == MessageRole.SYSTEM:
            from mistralai import SystemMessage
            return SystemMessage(content=self.content)
        else:
            raise ValueError(f"Unsupported message role: {self.role}")
