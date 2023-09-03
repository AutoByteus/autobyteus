# File path: autobyteus/llm_integrations/openai_integration/openai_message_types.py

"""
openai_message_types.py: Contains the data structures to represent and manage OpenAI messages.
"""

from abc import ABC
from enum import Enum, auto
from typing import List, Dict, Union

class OpenAIMessageRole(Enum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"

class BaseMessage(ABC):
    """Abstract Base Message class to represent a message."""
    
    role: OpenAIMessageRole = None  # Placeholder for the role, set in subclasses
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
    
    def __init__(self, content: str):
        super().__init__(content)

class AssistantMessage(BaseMessage):
    """Class representing an assistant's message."""
    
    role = OpenAIMessageRole.ASSISTANT  # Set the role specific to this subclass
    
    def __init__(self, content: str):
        super().__init__(content)

class MessageList:
    """Class to hold and manage a list of messages."""
    
    DEFAULT_SYSTEM_MESSAGE = SystemMessage("You are a helpful assistant.")
    
    def __init__(self):
        self.messages: List[BaseMessage] = []
    
    def add_system_message(self, content: str):
        # Insert the system message at the start of the list
        self.messages.insert(0, SystemMessage(content))
        
    def add_user_message(self, content: str):
        self.messages.append(UserMessage(content))
    
    def add_assistant_message(self, content: str):
        self.messages.append(AssistantMessage(content))
    
    def get_messages(self) -> List[Dict[str, Union[str, OpenAIMessageRole]]]:
        """Retrieve all messages. If no system message is present, prepend the default."""
        if not any(isinstance(msg, SystemMessage) for msg in self.messages):
            self.messages.insert(0, self.DEFAULT_SYSTEM_MESSAGE)
        return [msg.to_dict() for msg in self.messages]
