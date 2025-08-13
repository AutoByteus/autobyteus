# file: autobyteus/tests/unit_tests/tools/usage/providers/test_tool_manifest_provider.py
import pytest
import json
from unittest.mock import patch, MagicMock

from autobyteus.tools.usage.providers.tool_manifest_provider import ToolManifestProvider
from autobyteus.tools.registry import ToolDefinition
from autobyteus.llm.providers import LLMProvider
from autobyteus.tools.usage.registries.tool_formatter_pair import ToolFormatterPair
from autobyteus.tools.usage.formatters import DefaultXmlSchemaFormatter, BaseSchemaFormatter

@pytest.fixture
def mock_registry():
    with patch('autobyteus.tools.usage.providers.tool_manifest_provider.ToolFormattingRegistry') as MockRegistry:
        yield MockRegistry.return_value

@pytest.fixture
def provider(mock_registry):
    return ToolManifestProvider()

@pytest.fixture
def mock_tool_def():
    return MagicMock(spec=ToolDefinition)

def test_provide_uses_registry_and_formats_xml(provider: ToolManifestProvider, mock_registry: MagicMock, mock_tool_def: MagicMock):
    # Arrange
    mock_schema_formatter = MagicMock(spec=DefaultXmlSchemaFormatter)
    mock_schema_formatter.provide.return_value = "<tool name='TestTool' />"
    mock_example_formatter = MagicMock()
    mock_example_formatter.provide.return_value = "<tool name='TestTool'><arguments /></tool>"
    
    mock_pair = ToolFormatterPair(
        schema_formatter=mock_schema_formatter,
        example_formatter=mock_example_formatter
    )
    mock_registry.get_formatter_pair.return_value = mock_pair

    # Act
    manifest = provider.provide([mock_tool_def], provider=LLMProvider.ANTHROPIC)

    # Assert
    mock_registry.get_formatter_pair.assert_called_once_with(LLMProvider.ANTHROPIC)
    mock_schema_formatter.provide.assert_called_once_with(mock_tool_def)
    mock_example_formatter.provide.assert_called_once_with(mock_tool_def)

    assert "## Tool Definition:" in manifest
    assert "<tool name='TestTool' />" in manifest
    assert "## Example Usage:" in manifest
    assert "<tool name='TestTool'><arguments /></tool>" in manifest
    assert "\n\n---\n\n" not in manifest # Only one tool

def test_provide_uses_registry_and_formats_json(provider: ToolManifestProvider, mock_registry: MagicMock, mock_tool_def: MagicMock):
    # Arrange
    mock_schema_formatter = MagicMock(spec=BaseSchemaFormatter) # Not an XML formatter
    mock_schema_formatter.provide.return_value = {"name": "TestTool", "parameters": {}}
    mock_example_formatter = MagicMock()
    mock_example_formatter.provide.return_value = {"tool": {"function": "TestTool", "parameters": {}}}
    
    mock_pair = ToolFormatterPair(
        schema_formatter=mock_schema_formatter,
        example_formatter=mock_example_formatter
    )
    mock_registry.get_formatter_pair.return_value = mock_pair

    # Act
    manifest = provider.provide([mock_tool_def], provider=LLMProvider.OPENAI)

    # Assert
    mock_registry.get_formatter_pair.assert_called_once_with(LLMProvider.OPENAI)
    assert "## Tool Definition:" in manifest
    assert '{\n  "tool": {\n    "name": "TestTool",\n    "parameters": {}\n  }\n}' in manifest
    assert "## Example Usage:" not in manifest
    assert "To use this tool, you MUST output a JSON object" in manifest
    assert '{\n  "tool": {\n    "function": "TestTool",\n    "parameters": {}\n  }\n}' in manifest
    assert manifest.startswith("[\n")
    assert manifest.endswith("\n]")

def test_provide_joins_multiple_tools(provider: ToolManifestProvider, mock_registry: MagicMock):
    # Arrange
    mock_tool_1 = MagicMock(spec=ToolDefinition)
    mock_tool_2 = MagicMock(spec=ToolDefinition)
    
    mock_formatter = MagicMock(spec=DefaultXmlSchemaFormatter)
    mock_formatter.provide.side_effect = ["<tool name='Tool1' />", "<tool name='Tool2' />"]
    mock_example = MagicMock()
    mock_example.provide.side_effect = ["<example1 />", "<example2 />"]
    
    mock_pair = ToolFormatterPair(schema_formatter=mock_formatter, example_formatter=mock_example)
    mock_registry.get_formatter_pair.return_value = mock_pair

    # Act
    manifest = provider.provide([mock_tool_1, mock_tool_2], provider=LLMProvider.ANTHROPIC)

    # Assert
    assert "<tool name='Tool1' />" in manifest
    assert "<tool name='Tool2' />" in manifest
    assert "\n\n---\n\n" in manifest
