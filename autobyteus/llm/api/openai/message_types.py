# File path: autobyteus/llm_integrations/openai_integration/openai_message_types.py

"""
openai_message_types.py: Contains the data structures to represent and manage OpenAI messages.
"""

from abc import ABC
from enum import Enum, auto
from typing import List, Dict, Union
from abc import ABC

class OpenAIMessageRole(Enum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"

class BaseMessage(ABC):
    """Abstract Base Message class to represent a message."""
    
    role: OpenAIMessageRole  # Placeholder for the role, set in subclasses
    content: str
    
    def __init__(self, content: str):
        self.content = content

    def to_dict(self) -> Dict[str, str]:
        """Convert message to dictionary format."""
        return {"role": self.role.value, "content": self.content}

class SystemMessage(BaseMessage):
    """Class representing a system message."""
    
    role = OpenAIMessageRole.SYSTEM  # Set the role specific to this subclass
    
    def __init__(self, content: str):
        super().__init__(content)

class UserMessage(BaseMessage):
    """Class representing a user message."""
    
    role = OpenAIMessageRole.USER  # Set the role specific to this subclass
    

class AssistantMessage(BaseMessage):
    """Class representing an assistant's message."""
    
    role = OpenAIMessageRole.ASSISTANT  # Set the role specific to this subclass
    

class MessageList:
    def __init__(self, system_message: str = "You are a helpful assistant."):
        self.messages: List[BaseMessage] = []
        self.add_system_message(system_message)

    def add_system_message(self, content: str):
        self.messages = [SystemMessage(content)] + [
            msg for msg in self.messages 
            if not isinstance(msg, SystemMessage)
        ]

    def add_user_message(self, content: str):
        self.messages.append(UserMessage(content))
    
    def add_assistant_message(self, content: str):
        self.messages.append(AssistantMessage(content))

    def get_messages(self) -> List[Dict[str, str]]:
        """Retrieve all messages. If no system message is present, prepend the default."""
        return [msg.to_dict() for msg in self.messages]
    