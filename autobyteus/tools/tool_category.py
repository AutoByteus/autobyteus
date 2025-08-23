# file: autobyteus/autobyteus/tools/tool_category.py
from enum import Enum

class ToolCategory(str, Enum):
    """
    Provides standardized string constants for common tool categories.
    While tools can use any string for a category, using these constants
    is recommended to ensure consistency in UI grouping.
    """
    USER_INTERACTION = "User Interaction"
    FILE_SYSTEM = "File System"
    WEB = "Web"
    SYSTEM = "System"
    UTILITY = "Utility"
    AGENT_COMMUNICATION = "Agent Communication"
    PROMPT_MANAGEMENT = "Prompt Management"
    TASK_MANAGEMENT = "Task Management" # NEW CATEGORY ADDED
    GENERAL = "General"
    MCP = "MCP"
    MULTIMEDIA = "Multimedia"

    def __str__(self) -> str:
        return self.value
