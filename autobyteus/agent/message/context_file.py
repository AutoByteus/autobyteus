# file: autobyteus/autobyteus/agent/message/context_file.py
import os
import logging
from typing import Optional, Dict, Any
from dataclasses import dataclass, field

from .context_file_type import ContextFileType

logger = logging.getLogger(__name__)

@dataclass
class ContextFile:
    """
    Represents a single context file provided to an agent.
    This is a simple dataclass, deferring path validation and file access
    to input processors.
    """
    path: str
    file_type: ContextFileType = ContextFileType.UNKNOWN
    file_name: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """
        Called after the dataclass's __init__ method.
        Used here to infer file_name and file_type if not provided or UNKNOWN.
        """
        if self.file_name is None and self.path:
            try:
                self.file_name = os.path.basename(self.path)
            except Exception as e:
                logger.warning(f"Could not determine basename for path '{self.path}': {e}")
                self.file_name = "unknown_file"

        if self.file_type == ContextFileType.UNKNOWN and self.path:
            inferred_type = ContextFileType.from_path(self.path)
            if inferred_type != ContextFileType.UNKNOWN:
                self.file_type = inferred_type
                logger.debug(f"Inferred file type for '{self.path}' as {self.file_type.value}")
            else:
                logger.debug(f"Could not infer specific file type for '{self.path}', remaining UNKNOWN.")
        
        # Ensure path is a string
        if not isinstance(self.path, str):
            # This ideally should be caught by type hints earlier, but as a runtime safeguard:
            raise TypeError(f"ContextFile path must be a string, got {type(self.path)}")
            
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f"ContextFile initialized: path='{self.path}', type='{self.file_type.value}', name='{self.file_name}'")

    def to_dict(self) -> Dict[str, Any]:
        """Serializes the ContextFile to a dictionary."""
        return {
            "path": self.path,
            "file_type": self.file_type.value, # Serialize enum to its value
            "file_name": self.file_name,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ContextFile':
        """Deserializes a ContextFile from a dictionary."""
        if not isinstance(data.get("path"), str):
            raise ValueError("ContextFile 'path' in dictionary must be a string.")
        
        file_type_str = data.get("file_type", ContextFileType.UNKNOWN.value)
        try:
            file_type = ContextFileType(file_type_str)
        except ValueError:
            logger.warning(f"Invalid file_type string '{file_type_str}' in ContextFile data. Defaulting to UNKNOWN.")
            file_type = ContextFileType.UNKNOWN
            
        return cls(
            path=data["path"],
            file_type=file_type,
            file_name=data.get("file_name"),
            metadata=data.get("metadata", {})
        )

    def __repr__(self) -> str:
        return (f"ContextFile(path='{self.path}', file_name='{self.file_name}', "
                f"file_type='{self.file_type.value}', metadata_keys={list(self.metadata.keys())})")
