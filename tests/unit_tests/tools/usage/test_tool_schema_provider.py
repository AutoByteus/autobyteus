"""
Unit tests for ToolSchemaProvider.
"""
from unittest.mock import MagicMock

from autobyteus.tools.usage.tool_schema_provider import ToolSchemaProvider
from autobyteus.llm.providers import LLMProvider


def test_build_schema_returns_empty_for_missing_tools():
    registry = MagicMock()
    registry.get_tool_definition.return_value = None

    provider = ToolSchemaProvider(registry=registry)
    assert provider.build_schema(["missing_tool"], LLMProvider.OPENAI) == []


def test_build_schema_uses_formatter_for_definitions(monkeypatch):
    registry = MagicMock()
    tool_a = MagicMock()
    tool_b = MagicMock()
    tool_a.name = "tool_a"
    tool_b.name = "tool_b"
    registry.get_tool_definition.side_effect = [tool_a, tool_b]

    provider = ToolSchemaProvider(registry=registry)
    formatter = MagicMock()
    formatter.provide.side_effect = [{"name": "tool_a"}, {"name": "tool_b"}]

    monkeypatch.setattr(provider, "_select_formatter", lambda *_: formatter)

    schemas = provider.build_schema(["tool_a", "tool_b"], LLMProvider.OPENAI)
    assert schemas == [{"name": "tool_a"}, {"name": "tool_b"}]
    assert formatter.provide.call_count == 2
