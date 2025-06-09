# file: autobyteus/autobyteus/agent/message/agent_input_user_message.py
import logging
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field

from .context_file import ContextFile # Import the new ContextFile dataclass

logger = logging.getLogger(__name__)

@dataclass
class AgentInputUserMessage: 
    """
    Represents a message received from an external user interacting with the agent system.
    This is a simple dataclass. It includes support for a list of ContextFile objects, 
    allowing users to provide various documents as context.
    """
    content: str
    image_urls: Optional[List[str]] = field(default=None) # Basic list of strings
    context_files: Optional[List[ContextFile]] = field(default=None)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        # Basic type validation that dataclasses don't do automatically for mutable defaults or complex types
        if self.image_urls is not None and not (isinstance(self.image_urls, list) and all(isinstance(url, str) for url in self.image_urls)):
            raise TypeError("AgentInputUserMessage 'image_urls' must be a list of strings if provided.")
        if self.context_files is not None and not (isinstance(self.context_files, list) and all(isinstance(cf, ContextFile) for cf in self.context_files)):
            raise TypeError("AgentInputUserMessage 'context_files' must be a list of ContextFile objects if provided.")
        if not isinstance(self.metadata, dict): # Should be caught by default_factory, but good practice
             raise TypeError("AgentInputUserMessage 'metadata' must be a dictionary.")
        if not isinstance(self.content, str):
            raise TypeError("AgentInputUserMessage 'content' must be a string.")

        if logger.isEnabledFor(logging.DEBUG):
            num_context_files = len(self.context_files) if self.context_files else 0
            logger.debug(
                f"AgentInputUserMessage initialized. Content: '{self.content[:50]}...', "
                f"Image URLs: {self.image_urls}, Num ContextFiles: {num_context_files}, "
                f"Metadata keys: {list(self.metadata.keys())}"
            )

    def to_dict(self) -> Dict[str, Any]:
        """Serializes the AgentInputUserMessage to a dictionary."""
        # Manually handle serialization of list of ContextFile objects
        context_files_dict_list = None
        if self.context_files:
            context_files_dict_list = [cf.to_dict() for cf in self.context_files]

        return {
            "content": self.content,
            "image_urls": self.image_urls,
            "context_files": context_files_dict_list,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AgentInputUserMessage':
        """Deserializes an AgentInputUserMessage from a dictionary."""
        content = data.get("content")
        if not isinstance(content, str): # Ensure content is string
            raise ValueError("AgentInputUserMessage 'content' in dictionary must be a string.")

        image_urls = data.get("image_urls")
        if image_urls is not None and not (isinstance(image_urls, list) and all(isinstance(url, str) for url in image_urls)):
            raise ValueError("AgentInputUserMessage 'image_urls' in dictionary must be a list of strings if provided.")

        context_files_data = data.get("context_files")
        context_files_list: Optional[List[ContextFile]] = None
        if context_files_data is not None:
            if not isinstance(context_files_data, list):
                raise ValueError("AgentInputUserMessage 'context_files' in dictionary must be a list if provided.")
            context_files_list = [ContextFile.from_dict(cf_data) for cf_data in context_files_data]
        
        metadata = data.get("metadata", {})
        if not isinstance(metadata, dict):
            raise ValueError("AgentInputUserMessage 'metadata' in dictionary must be a dict if provided.")

        return cls(
            content=content,
            image_urls=image_urls,
            context_files=context_files_list,
            metadata=metadata
        )

    def __repr__(self) -> str:
        content_preview = f"{self.content[:100]}..." if len(self.content) > 100 else self.content
        images_repr = f", image_urls={self.image_urls}" if self.image_urls else ""
        
        if self.context_files:
            context_repr = f", context_files=[{len(self.context_files)} ContextFile(s)]"
        else:
            context_repr = ""
            
        meta_repr = f", metadata_keys={list(self.metadata.keys())}" if self.metadata else ""
        
        return (f"AgentInputUserMessage(content='{content_preview}'"
                f"{images_repr}{context_repr}{meta_repr})")
