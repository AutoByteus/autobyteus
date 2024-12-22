from typing import Dict, Union, List
from enum import Enum


class MessageRole(Enum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"


class Message:
    def __init__(self, role: MessageRole, content: Union[str, List[Dict]]):
        self.role = role
        self.content = content

    def to_dict(self) -> Dict[str, str]:
        return {"role": self.role.value, "content": self.content}

    def to_mistral_message(self):
        if self.role == MessageRole.USER:
            from mistralai import UserMessage
            from mistralai.models.contentchunk import TextChunk, ImageURLChunk

            # Simple text message
            if isinstance(self.content, str):
                return UserMessage(content=self.content)

            # List of content (mixed text/images)
            elif isinstance(self.content, list):
                chunks = []
                for item in self.content:
                    if item.get("type") == "text":
                        chunks.append(TextChunk(text=item["content"]))
                    elif item.get("type") == "image_url":
                        chunks.append(ImageURLChunk(image_url=item["image_url"]["url"]))
                return UserMessage(content=chunks)

        elif self.role == MessageRole.ASSISTANT:
            from mistralai import AssistantMessage

            return AssistantMessage(content=self.content)
