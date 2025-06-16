# file: autobyteus/tests/unit_tests/tools/usage/providers/test_json_schema_provider.py
import pytest
from unittest.mock import patch, MagicMock

from autobyteus.tools.usage.providers.json_schema_provider import JsonSchemaProvider
from autobyteus.tools.registry import ToolDefinition
from autobyteus.llm.providers import LLMProvider

@pytest.fixture
def mock_tool_def():
    return MagicMock(spec=ToolDefinition)

def test_provider_uses_registry_with_provider(mock_tool_def: MagicMock):
    """
    Tests that the provider uses the registry to get a specific formatter
    when an LLM provider is specified.
    """
    patch_target = 'autobyteus.tools.usage.providers.json_schema_provider.JsonSchemaFormatterRegistry'
    with patch(patch_target) as MockRegistry:
        mock_registry_instance = MockRegistry.return_value
        mock_formatter = MagicMock()
        mock_formatter.provide.return_value = {"name": "specific_format"}
        mock_registry_instance.get_formatter.return_value = mock_formatter

        provider = JsonSchemaProvider()
        result = provider.provide(mock_tool_def, llm_provider=LLMProvider.OPENAI)

        assert result == {"name": "specific_format"}
        MockRegistry.assert_called_once()
        mock_registry_instance.get_formatter.assert_called_once_with(LLMProvider.OPENAI)
        mock_formatter.provide.assert_called_once_with(mock_tool_def)

def test_provider_uses_registry_default(mock_tool_def: MagicMock):
    """
    Tests that the provider uses the registry to get the default formatter
    when no LLM provider is specified.
    """
    patch_target = 'autobyteus.tools.usage.providers.json_schema_provider.JsonSchemaFormatterRegistry'
    with patch(patch_target) as MockRegistry:
        mock_registry_instance = MockRegistry.return_value
        mock_formatter = MagicMock()
        mock_formatter.provide.return_value = {"name": "default_format"}
        mock_registry_instance.get_default_formatter.return_value = mock_formatter

        provider = JsonSchemaProvider()
        result = provider.provide(mock_tool_def, llm_provider=None)

        assert result == {"name": "default_format"}
        MockRegistry.assert_called_once()
        mock_registry_instance.get_default_formatter.assert_called_once()
        mock_formatter.provide.assert_called_once_with(mock_tool_def)
