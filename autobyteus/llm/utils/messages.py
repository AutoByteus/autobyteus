from typing import Dict, Union, List, Optional
from enum import Enum

class MessageRole(Enum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"

class Message:
    def __init__(self,
                 role: MessageRole,
                 content: Optional[str] = None,
                 reasoning_content: Optional[str] = None,
                 image_urls: Optional[List[str]] = None,
                 audio_urls: Optional[List[str]] = None,
                 video_urls: Optional[List[str]] = None):
        """
        Initializes a rich Message object for conversation history.

        Args:
            role: The role of the message originator.
            content: The textual content of the message.
            reasoning_content: Optional reasoning/thought process from an assistant.
            image_urls: Optional list of image URIs.
            audio_urls: Optional list of audio URIs.
            video_urls: Optional list of video URIs.
        """
        self.role = role
        self.content = content
        self.reasoning_content = reasoning_content
        self.image_urls = image_urls or []
        self.audio_urls = audio_urls or []
        self.video_urls = video_urls or []

    def to_dict(self) -> Dict[str, Union[str, List[str], None]]:
        """
        Returns a simple dictionary representation of the Message object.
        This is for internal use and does not format for any specific API.
        """
        return {
            "role": self.role.value,
            "content": self.content,
            "reasoning_content": self.reasoning_content,
            "image_urls": self.image_urls,
            "audio_urls": self.audio_urls,
            "video_urls": self.video_urls,
        }
