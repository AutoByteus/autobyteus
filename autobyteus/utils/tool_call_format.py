"""
Helpers for resolving tool-call format selection.
"""
from __future__ import annotations

import os


ENV_TOOL_CALL_FORMAT = "AUTOBYTEUS_STREAM_PARSER"
_VALID_FORMATS = {"xml", "json", "sentinel", "api_tool_call"}


def resolve_tool_call_format() -> str:
    """
    Resolve the tool-call format from environment.

    Returns one of: "xml", "json", "sentinel", "api_tool_call".
    Defaults to "api_tool_call" when unset/invalid.
    """
    value = os.getenv(ENV_TOOL_CALL_FORMAT)
    if not value:
        return "api_tool_call"
    value = value.strip().lower()
    if value in _VALID_FORMATS:
        return value
    return "api_tool_call"


def is_xml_tool_format() -> bool:
    """Return True if tool-call format is forced to XML by environment."""
    return resolve_tool_call_format() == "xml"


def is_json_tool_format() -> bool:
    """Return True if tool-call format is forced to JSON by environment."""
    return resolve_tool_call_format() == "json"
