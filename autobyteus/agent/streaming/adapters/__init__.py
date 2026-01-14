"""Shared adapters for streaming output."""

from .invocation_adapter import ToolInvocationAdapter
from .tool_syntax_registry import (
    ToolSyntaxSpec,
    get_tool_syntax_spec,
    tool_syntax_registry_items,
)
from .tool_call_parsing import parse_json_tool_call, parse_xml_arguments

__all__ = [
    "ToolInvocationAdapter",
    "ToolSyntaxSpec",
    "get_tool_syntax_spec",
    "tool_syntax_registry_items",
    "parse_json_tool_call",
    "parse_xml_arguments",
]
