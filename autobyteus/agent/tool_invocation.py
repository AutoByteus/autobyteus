# file: autobyteus/autobyteus/agent/tool_invocation.py
import uuid
from typing import Optional, Dict, Any

class ToolInvocation:
    def __init__(self, name: Optional[str] = None, arguments: Optional[Dict[str, Any]] = None, id: Optional[str] = None):
        """
        Represents a tool invocation request.

        Args:
            name: The name of the tool to be invoked.
            arguments: A dictionary of arguments for the tool.
            id: Optional. A unique identifier for this tool invocation.
                If None, a new UUID will be generated.
        """
        self.name: Optional[str] = name
        self.arguments: Optional[Dict[str, Any]] = arguments
        self.id: str = id if id is not None else str(uuid.uuid4())

    def is_valid(self) -> bool:
        """
        Checks if the tool invocation has a name and arguments.
        The 'id' is always present (auto-generated if not provided).
        """
        return self.name is not None and self.arguments is not None

    def __repr__(self) -> str:
        return (f"ToolInvocation(id='{self.id}', name='{self.name}', "
                f"arguments={self.arguments})")

