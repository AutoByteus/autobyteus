# file: autobyteus/autobyteus/tools/tool_category.py
from enum import Enum

class ToolCategory(str, Enum):
    """Enumeration of tool categories to identify their origin."""
    LOCAL = "local"
    MCP = "mcp"
    # BUILT_IN, USER_DEFINED etc. could be added later.

    def __str__(self) -> str:
        return self.value
