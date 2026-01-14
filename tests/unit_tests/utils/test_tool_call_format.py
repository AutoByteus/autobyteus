"""
Unit tests for tool call format resolution.
"""
import os

from autobyteus.utils.tool_call_format import resolve_tool_call_format


def test_resolve_tool_call_format_native_alias(monkeypatch):
    monkeypatch.setenv("AUTOBYTEUS_STREAM_PARSER", "native")
    assert resolve_tool_call_format() == "api_tool_call"


def test_resolve_tool_call_format_api_tool_call(monkeypatch):
    monkeypatch.setenv("AUTOBYTEUS_STREAM_PARSER", "api_tool_call")
    assert resolve_tool_call_format() == "api_tool_call"
