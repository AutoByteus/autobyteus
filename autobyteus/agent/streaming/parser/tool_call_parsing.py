"""Compatibility shim for tool call parsing utilities."""
from ..adapters.tool_call_parsing import *

__all__ = ["parse_json_tool_call", "parse_xml_arguments"]
