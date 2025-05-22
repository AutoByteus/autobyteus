# file: autobyteus/autobyteus/llm/user_message.py
import logging
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)

class LLMUserMessage:
    """
    Represents a user message formatted specifically for input to an LLM.
    It includes content and optionally image URLs.
    This structure is typically used when constructing prompts for multimodal LLMs
    or when sending a "user" role message in a conversation.
    """
    def __init__(self,
                 content: str,
                 image_urls: Optional[List[str]] = None):
        """
        Initializes an LLMUserMessage.

        Args:
            content: The textual content of the user's message.
            image_urls: An optional list of URLs or local paths to images
                        to be included with the message for the LLM.
        """
        if not isinstance(content, str):
            # Allow empty string for content, as images might be the only input.
            # But content must still be a string type.
            pass # Validation can be more strict if empty content is disallowed with no images
        
        if image_urls is None:
            image_urls = [] # Default to empty list for easier processing

        if not (isinstance(image_urls, list) and all(isinstance(url, str) for url in image_urls)):
            raise TypeError("LLMUserMessage 'image_urls' must be a list of strings.")
        
        if not content and not image_urls:
            raise ValueError("LLMUserMessage must have either content or image_urls or both.")

        self.content: str = content
        self.image_urls: List[str] = image_urls

        logger.debug(f"LLMUserMessage created. Content: '{content[:50]}...', Image URLs: {image_urls}")

    def __repr__(self) -> str:
        image_urls_repr = f", image_urls={self.image_urls}" if self.image_urls else ""
        return f"LLMUserMessage(content='{self.content[:100]}...'{image_urls_repr})"

    def to_dict(self) -> Dict[str, Any]:
        """
        Serializes the LLMUserMessage to a dictionary. This method might be less used
        now that BaseLLM._add_user_message handles the conversion to the Message format.
        Kept for potential direct use or testing.
        """
        data = {"content": self.content}
        if self.image_urls:
            data["image_urls"] = self.image_urls
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'LLMUserMessage':
        """
        Deserializes an LLMUserMessage from a dictionary.
        """
        content = data.get("content", "") # Default to empty string if not present
        image_urls = data.get("image_urls") # Expects a list or None

        # Basic validation, more can be added if needed
        if not isinstance(content, str):
             raise ValueError("LLMUserMessage 'content' in dictionary must be a string.")
        if image_urls is not None and not (isinstance(image_urls, list) and all(isinstance(url, str) for url in image_urls)):
            raise ValueError("LLMUserMessage 'image_urls' in dictionary must be a list of strings if provided.")

        return cls(content=content, image_urls=image_urls)
