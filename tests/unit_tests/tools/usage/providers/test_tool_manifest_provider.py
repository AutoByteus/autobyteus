# file: autobyteus/tests/unit_tests/tools/usage/providers/test_tool_manifest_provider.py
import pytest
import json
from unittest.mock import patch, MagicMock

from autobyteus.tools.usage.providers.tool_manifest_provider import ToolManifestProvider
from autobyteus.tools.registry import ToolDefinition
from autobyteus.llm.providers import LLMProvider
from autobyteus.tools.usage.registries.tool_formatter_pair import ToolFormatterPair
from autobyteus.tools.usage.formatters import BaseXmlSchemaFormatter, BaseSchemaFormatter

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
    mock_schema_formatter = MagicMock(spec=BaseXmlSchemaFormatter)
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
    mock_example_formatter.provide.return_value = {"example": "usage"}
    
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
    # Check for direct JSON dump of schema, without the extra 'tool' wrapper
    assert '{\n  "name": "TestTool",\n  "parameters": {}\n}' in manifest
    # Check for the new, more descriptive example header
    assert "Example: To use this tool, you could provide the following JSON object as a tool call:" in manifest
    # Check for the JSON dump of the example
    assert '{\n  "example": "usage"\n}' in manifest
    # Check that the manifest is NOT wrapped in brackets
    assert not manifest.startswith("[")
    assert not manifest.endswith("]")
    # Check that there is no separator for a single tool
    assert "\n\n---\n\n" not in manifest

def test_provide_joins_multiple_xml_tools(provider: ToolManifestProvider, mock_registry: MagicMock):
    # Arrange
    mock_tool_1 = MagicMock(spec=ToolDefinition)
    mock_tool_2 = MagicMock(spec=ToolDefinition)
    
    mock_formatter = MagicMock(spec=BaseXmlSchemaFormatter)
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

def test_provide_joins_multiple_json_tools(provider: ToolManifestProvider, mock_registry: MagicMock):
    # Arrange
    mock_tool_1 = MagicMock(spec=ToolDefinition, name="Tool1")
    mock_tool_2 = MagicMock(spec=ToolDefinition, name="Tool2")
    
    mock_schema_formatter = MagicMock(spec=BaseSchemaFormatter)
    mock_schema_formatter.provide.side_effect = [
        {"name": "Tool1", "params": {}},
        {"name": "Tool2", "params": {}}
    ]
    mock_example_formatter = MagicMock()
    mock_example_formatter.provide.side_effect = [
        {"example": "one"},
        {"example": "two"}
    ]
    
    mock_pair = ToolFormatterPair(
        schema_formatter=mock_schema_formatter,
        example_formatter=mock_example_formatter
    )
    mock_registry.get_formatter_pair.return_value = mock_pair

    # Act
    manifest = provider.provide([mock_tool_1, mock_tool_2], provider=LLMProvider.OPENAI)

    # Assert
    # Check for content from both tools
    assert '"name": "Tool1"' in manifest
    assert '"example": "one"' in manifest
    assert '"name": "Tool2"' in manifest
    assert '"example": "two"' in manifest
    # Check for the correct separator
    assert "\n\n---\n\n" in manifest
    # Check that the manifest is NOT wrapped in brackets
    assert not manifest.startswith("[")
    assert not manifest.endswith("]")
