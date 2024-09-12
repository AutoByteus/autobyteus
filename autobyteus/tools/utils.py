from typing import List
from autobyteus.tools.base_tool import BaseTool

def format_tool_usage_info(tools: List[BaseTool]) -> str:
    """
    Format usage information for a list of tools into a single string.

    Args:
        tools (List[BaseTool]): A list of BaseTool instances.

    Returns:
        str: A formatted string containing the usage information for all tools.
    """
    tool_usage_info = ""
    for i, tool in enumerate(tools):
        tool_usage_info += f"  {i + 1} {tool.tool_usage_xml()}\n\n"
    return tool_usage_info.strip()
