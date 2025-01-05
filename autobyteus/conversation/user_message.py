
from typing import List, Optional, Dict, Any

class UserMessage:
    """
    Represents a message from a user in the automated coding workflow system.
    This class encapsulates both the message content and any additional metadata
    through keyword arguments.

    Attributes:
        content (str): 
            The actual message content to be processed by the agent.
            This could be a coding requirement, a question, or any other input.

        file_paths (List[str], optional): 
            List of paths to files that provide additional context for the message.
            For example, paths to code files, images, or documentation relevant
            to the user's request.

        kwargs: 
            Any additional keyword arguments provided during initialization are stored
            as attributes of the message object. For example:
            
            UserMessage("content", original_query="raw input", priority="high")
            
            This creates a message with .original_query and .priority attributes.
    """

    def __init__(self, 
                 content: str, 
                 file_paths: Optional[List[str]] = None,
                 **kwargs):
        """
        Initialize a new UserMessage instance.

        Args:
            content: The message content to be processed
            file_paths: Optional list of relevant file paths
            **kwargs: Additional attributes to store with the message
        """
        self.content = content
        self.file_paths = file_paths or []
        
        # Store each kwarg as an attribute
        for key, value in kwargs.items():
            setattr(self, key, value)

    def __str__(self) -> str:
        """Returns a string representation of the UserMessage for debugging."""
        attrs = {
            key: value for key, value in vars(self).items() 
            if key not in ('content', 'file_paths')
        }
        return (f"UserMessage(\n"
                f"    content={self.content!r},\n"
                f"    file_paths={self.file_paths!r},\n"
                f"    **{attrs}\n"
                f")")

