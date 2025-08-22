# file: autobyteus/autobyteus/llm/user_message.py
import logging
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)

class LLMUserMessage:
    """
    Represents a user message formatted specifically for input to an LLM.
    It includes content and optionally URLs for various media types.
    This structure is typically used when constructing prompts for multimodal LLMs.
    """
    def __init__(self,
                 content: str,
                 image_urls: Optional[List[str]] = None,
                 audio_urls: Optional[List[str]] = None,
                 video_urls: Optional[List[str]] = None):
        """
        Initializes an LLMUserMessage.

        Args:
            content: The textual content of the user's message.
            image_urls: An optional list of URLs or local paths to images.
            audio_urls: An optional list of URLs or local paths to audio files.
            video_urls: An optional list of URLs or local paths to video files.
        """
        self.content: str = content
        self.image_urls: List[str] = image_urls or []
        self.audio_urls: List[str] = audio_urls or []
        self.video_urls: List[str] = video_urls or []

        # --- Validation ---
        if not isinstance(self.content, str):
            raise TypeError("LLMUserMessage 'content' must be a string.")
        if not (isinstance(self.image_urls, list) and all(isinstance(url, str) for url in self.image_urls)):
            raise TypeError("LLMUserMessage 'image_urls' must be a list of strings.")
        if not (isinstance(self.audio_urls, list) and all(isinstance(url, str) for url in self.audio_urls)):
            raise TypeError("LLMUserMessage 'audio_urls' must be a list of strings.")
        if not (isinstance(self.video_urls, list) and all(isinstance(url, str) for url in self.video_urls)):
            raise TypeError("LLMUserMessage 'video_urls' must be a list of strings.")

        if not self.content and not self.image_urls and not self.audio_urls and not self.video_urls:
            raise ValueError("LLMUserMessage must have either content or at least one media URL.")

        logger.debug(f"LLMUserMessage created. Content: '{self.content[:50]}...', "
                     f"Images: {len(self.image_urls)}, Audio: {len(self.audio_urls)}, Video: {len(self.video_urls)}")

    def __repr__(self) -> str:
        parts = [f"content='{self.content[:100]}...'"]
        if self.image_urls:
            parts.append(f"image_urls={self.image_urls}")
        if self.audio_urls:
            parts.append(f"audio_urls={self.audio_urls}")
        if self.video_urls:
            parts.append(f"video_urls={self.video_urls}")
        return f"LLMUserMessage({', '.join(parts)})"

    def to_dict(self) -> Dict[str, Any]:
        """
        Serializes the LLMUserMessage to a dictionary.
        """
        data = {"content": self.content}
        if self.image_urls:
            data["image_urls"] = self.image_urls
        if self.audio_urls:
            data["audio_urls"] = self.audio_urls
        if self.video_urls:
            data["video_urls"] = self.video_urls
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'LLMUserMessage':
        """
        Deserializes an LLMUserMessage from a dictionary.
        """
        return cls(
            content=data.get("content", ""),
            image_urls=data.get("image_urls"),
            audio_urls=data.get("audio_urls"),
            video_urls=data.get("video_urls")
        )
