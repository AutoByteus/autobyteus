# file: autobyteus/autobyteus/tools/tool_origin.py
from enum import Enum

class ToolOrigin(str, Enum):
    """Enumeration of tool origins to identify their execution model."""
    LOCAL = "local"
    MCP = "mcp"

    def __str__(self) -> str:
        return self.value
