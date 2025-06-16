# file: autobyteus/tests/unit_tests/tools/registry/test_tool_definition.py
import pytest
from unittest.mock import patch, MagicMock

from autobyteus.tools.registry import ToolDefinition
from autobyteus.tools.parameter_schema import ParameterSchema, ParameterDefinition, ParameterType
from autobyteus.llm.providers import LLMProvider

@pytest.fixture
def sample_tool_def() -> ToolDefinition:
    """Provides a basic ToolDefinition for testing."""
    schema = ParameterSchema()
    schema.add_parameter(ParameterDefinition(name="param1", param_type=ParameterType.STRING, description="A test parameter."))
    return ToolDefinition(
        name="MyTestTool",
        description="A tool for testing.",
        argument_schema=schema,
        tool_class=MagicMock
    )

def test_get_usage_xml(sample_tool_def: ToolDefinition):
    """Tests the on-demand XML schema generation."""
    with patch('autobyteus.tools.registry.tool_definition.XmlSchemaProvider') as MockXmlProvider:
        mock_provider_instance = MockXmlProvider.return_value
        mock_provider_instance.provide.return_value = "<tool name='MyTestTool'>...</tool>"

        xml_string = sample_tool_def.get_usage_xml(provider=LLMProvider.OPENAI)

        assert xml_string == "<tool name='MyTestTool'>...</tool>"
        MockXmlProvider.assert_called_once()
        mock_provider_instance.provide.assert_called_once_with(sample_tool_def, llm_provider=LLMProvider.OPENAI)

def test_get_usage_json_default(sample_tool_def: ToolDefinition):
    """Tests the on-demand default JSON schema generation."""
    with patch('autobyteus.tools.registry.tool_definition.JsonSchemaProvider') as MockJsonProvider:
        mock_provider_instance = MockJsonProvider.return_value
        mock_provider_instance.provide.return_value = {"name": "MyTestTool", "inputSchema": {}}

        json_dict = sample_tool_def.get_usage_json()

        assert json_dict == {"name": "MyTestTool", "inputSchema": {}}
        MockJsonProvider.assert_called_once()
        mock_provider_instance.provide.assert_called_once_with(sample_tool_def, llm_provider=None)


def test_get_usage_json_with_provider(sample_tool_def: ToolDefinition):
    """Tests the on-demand provider-specific JSON schema generation."""
    with patch('autobyteus.tools.registry.tool_definition.JsonSchemaProvider') as MockJsonProvider:
        mock_provider_instance = MockJsonProvider.return_value
        mock_provider_instance.provide.return_value = {"type": "function", "function": {"name": "MyTestTool"}}
        
        provider = LLMProvider.OPENAI
        json_dict = sample_tool_def.get_usage_json(provider=provider)
        
        assert json_dict == {"type": "function", "function": {"name": "MyTestTool"}}
        mock_provider_instance.provide.assert_called_once_with(sample_tool_def, llm_provider=provider)

def test_get_usage_xml_example(sample_tool_def: ToolDefinition):
    """Tests the on-demand XML example generation."""
    with patch('autobyteus.tools.registry.tool_definition.XmlExampleProvider') as MockXmlExProvider:
        mock_provider_instance = MockXmlExProvider.return_value
        mock_provider_instance.provide.return_value = "<tool_call name='MyTestTool'>...</tool_call>"

        xml_string = sample_tool_def.get_usage_xml_example(provider=LLMProvider.MISTRAL)
        
        assert xml_string == "<tool_call name='MyTestTool'>...</tool_call>"
        MockXmlExProvider.assert_called_once()
        mock_provider_instance.provide.assert_called_once_with(sample_tool_def, llm_provider=LLMProvider.MISTRAL)

def test_get_usage_json_example(sample_tool_def: ToolDefinition):
    """Tests the on-demand JSON example generation."""
    with patch('autobyteus.tools.registry.tool_definition.JsonExampleProvider') as MockJsonExProvider:
        mock_provider_instance = MockJsonExProvider.return_value
        mock_provider_instance.provide.return_value = {"id": "call_123", "type": "function", "function": {}}

        json_dict = sample_tool_def.get_usage_json_example(provider=LLMProvider.MISTRAL)

        assert json_dict["id"] == "call_123"
        mock_provider_instance.provide.assert_called_once_with(sample_tool_def, llm_provider=LLMProvider.MISTRAL)
