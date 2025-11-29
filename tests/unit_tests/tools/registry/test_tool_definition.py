# file: autobyteus/tests/unit_tests/tools/registry/test_tool_definition.py
import pytest
from unittest.mock import MagicMock, patch

from autobyteus.tools.registry import ToolDefinition
from autobyteus.utils.parameter_schema import ParameterSchema
from autobyteus.llm.providers import LLMProvider
from autobyteus.tools.tool_origin import ToolOrigin
from autobyteus.tools.tool_category import ToolCategory

@pytest.fixture
def mock_schema_provider() -> MagicMock:
    """Provides a mock schema provider function."""
    schema = ParameterSchema()
    return MagicMock(return_value=schema)

@pytest.fixture
def sample_tool_def(mock_schema_provider: MagicMock) -> ToolDefinition:
    """Provides a basic ToolDefinition for testing using the new provider-based constructor."""
    return ToolDefinition(
        name="MyTestTool",
        description="A tool for testing.",
        origin=ToolOrigin.LOCAL,
        category=ToolCategory.GENERAL,
        argument_schema_provider=mock_schema_provider,
        config_schema_provider=lambda: None,
        tool_class=MagicMock # Pass the class/type, not an instance
    )

def test_schema_provider_is_called_once_and_cached(sample_tool_def: ToolDefinition, mock_schema_provider: MagicMock):
    """Tests that the schema provider is called on first access and the result is cached."""
    # First access
    schema1 = sample_tool_def.argument_schema
    mock_schema_provider.assert_called_once()
    assert schema1 is not None

    # Second access
    schema2 = sample_tool_def.argument_schema
    # The call count should still be 1 because the result is cached
    mock_schema_provider.assert_called_once()
    assert schema2 is schema1

def test_reload_cached_schema_eagerly_regenerates(sample_tool_def: ToolDefinition, mock_schema_provider: MagicMock):
    """Tests that reloading the cache eagerly calls the provider and updates the cache."""
    # First access to populate the cache
    _ = sample_tool_def.argument_schema
    mock_schema_provider.assert_called_once()

    # Eagerly reload the cache. This should immediately call the provider again.
    sample_tool_def.reload_cached_schema()
    assert mock_schema_provider.call_count == 2

    # Subsequent access should not call the provider again, as the cache is now repopulated.
    _ = sample_tool_def.argument_schema
    assert mock_schema_provider.call_count == 2

def test_reload_cached_schema_refreshes_description():
    """Tests that reloading also refreshes the description when a provider is available."""
    schema_provider = MagicMock(return_value=ParameterSchema())
    description_provider = MagicMock(return_value="New description")

    tool_def = ToolDefinition(
        name="DescReloadTool",
        description="Old description",
        origin=ToolOrigin.LOCAL,
        category=ToolCategory.GENERAL,
        argument_schema_provider=schema_provider,
        config_schema_provider=lambda: None,
        tool_class=MagicMock,  # Still need a class or factory
        description_provider=description_provider
    )

    assert tool_def.description == "Old description"

    tool_def.reload_cached_schema()

    assert tool_def.description == "New description"
    # Provider should have been called during reload.
    description_provider.assert_called_once()

def test_get_usage_xml(sample_tool_def: ToolDefinition):
    """Tests the on-demand XML schema generation."""
    with patch('autobyteus.tools.registry.tool_definition.DefaultXmlSchemaFormatter') as MockFormatter:
        mock_formatter_instance = MockFormatter.return_value
        mock_formatter_instance.provide.return_value = "<tool name='MyTestTool'>...</tool>"

        xml_string = sample_tool_def.get_usage_xml()

        assert xml_string == "<tool name='MyTestTool'>...</tool>"
        MockFormatter.assert_called_once()
        mock_formatter_instance.provide.assert_called_once_with(sample_tool_def)

def test_get_usage_json(sample_tool_def: ToolDefinition):
    """Tests the on-demand default JSON schema generation."""
    with patch('autobyteus.tools.registry.tool_definition.DefaultJsonSchemaFormatter') as MockFormatter:
        mock_formatter_instance = MockFormatter.return_value
        mock_formatter_instance.provide.return_value = {"name": "MyTestTool", "inputSchema": {}}

        json_dict = sample_tool_def.get_usage_json()

        assert json_dict == {"name": "MyTestTool", "inputSchema": {}}
        MockFormatter.assert_called_once()
        mock_formatter_instance.provide.assert_called_once_with(sample_tool_def)

def test_get_usage_xml_example(sample_tool_def: ToolDefinition):
    """Tests the on-demand XML example generation."""
    with patch('autobyteus.tools.registry.tool_definition.DefaultXmlExampleFormatter') as MockFormatter:
        mock_formatter_instance = MockFormatter.return_value
        mock_formatter_instance.provide.return_value = "<tool name='MyTestTool'>...</tool>"

        xml_string = sample_tool_def.get_usage_xml_example()
        
        assert xml_string == "<tool name='MyTestTool'>...</tool>"
        MockFormatter.assert_called_once()
        mock_formatter_instance.provide.assert_called_once_with(sample_tool_def)

def test_get_usage_json_example(sample_tool_def: ToolDefinition):
    """Tests the on-demand JSON example generation."""
    with patch('autobyteus.tools.registry.tool_definition.DefaultJsonExampleFormatter') as MockFormatter:
        mock_formatter_instance = MockFormatter.return_value
        mock_formatter_instance.provide.return_value = {"tool": {"function": "MyTestTool"}}

        json_dict = sample_tool_def.get_usage_json_example()

        assert json_dict["tool"]["function"] == "MyTestTool"
        MockFormatter.assert_called_once()
        mock_formatter_instance.provide.assert_called_once_with(sample_tool_def)
