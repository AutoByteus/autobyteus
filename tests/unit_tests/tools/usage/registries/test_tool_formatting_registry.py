# file: autobyteus/tests/unit_tests/tools/usage/registries/test_tool_formatting_registry.py
import pytest
from unittest.mock import MagicMock, patch
from autobyteus.tools.usage.registries.tool_formatting_registry import ToolFormattingRegistry, register_tool_formatter
from autobyteus.llm.providers import LLMProvider
from autobyteus.tools.usage.formatters import (
    OpenAiJsonSchemaFormatter, OpenAiJsonExampleFormatter,
    DefaultXmlSchemaFormatter, DefaultXmlExampleFormatter,
    DefaultJsonSchemaFormatter, DefaultJsonExampleFormatter
)
from autobyteus.tools.usage.registries.tool_formatter_pair import ToolFormatterPair
from autobyteus.tools import BaseSchemaFormatter, BaseExampleFormatter


@pytest.fixture(autouse=True)
def mock_env_override():
    # Force no override to ensure deterministic test results for default providers
    with patch('autobyteus.tools.usage.registries.tool_formatting_registry.resolve_tool_call_format', return_value=None):
        yield

@pytest.fixture
def registry():
    # Use a new instance for each test to avoid singleton state issues
    # Note: SingletonMeta might still persist state, ideally we reset it or mock __init__
    # But for these tests, we are mostly checking `get_formatter_pair` logic which is instance method
    reg = ToolFormattingRegistry()
    # Reset the tool pairs to default state if needed, or rely on logic not to mutate persistently across tests
    return reg

def test_get_openai_json_pair(registry: ToolFormattingRegistry):
    pair = registry.get_formatter_pair(LLMProvider.OPENAI)
    assert isinstance(pair, ToolFormatterPair)
    assert isinstance(pair.schema_formatter, OpenAiJsonSchemaFormatter)
    assert isinstance(pair.example_formatter, OpenAiJsonExampleFormatter)

def test_get_anthropic_xml_pair(registry: ToolFormattingRegistry):
    pair = registry.get_formatter_pair(LLMProvider.ANTHROPIC)
    assert isinstance(pair, ToolFormatterPair)
    assert isinstance(pair.schema_formatter, DefaultXmlSchemaFormatter)
    assert isinstance(pair.example_formatter, DefaultXmlExampleFormatter)

def test_get_default_pair_for_unregistered_provider(registry: ToolFormattingRegistry):
    # Kimi is not explicit in the map, so it should get the default JSON pair
    pair = registry.get_formatter_pair(LLMProvider.KIMI)
    assert isinstance(pair, ToolFormatterPair)
    assert isinstance(pair.schema_formatter, DefaultJsonSchemaFormatter)
    assert isinstance(pair.example_formatter, DefaultJsonExampleFormatter)

def test_get_default_pair_for_none_provider(registry: ToolFormattingRegistry):
    pair = registry.get_formatter_pair(None)
    assert isinstance(pair, ToolFormatterPair)
    assert isinstance(pair.schema_formatter, DefaultJsonSchemaFormatter)
    assert isinstance(pair.example_formatter, DefaultJsonExampleFormatter)

def test_register_tool_formatter_facade():
    """
    Test that the facade correctly creates a pair and calls the registry.
    """
    # Use patch to mock the registry retrieval within the function
    with patch('autobyteus.tools.usage.registries.tool_formatting_registry.ToolFormattingRegistry') as MockRegistry:
        mock_registry_instance = MockRegistry.return_value
        
        mock_schema_formatter = MagicMock(spec=BaseSchemaFormatter)
        mock_example_formatter = MagicMock(spec=BaseExampleFormatter)
        
        tool_name = "test_custom_tool"
        
        # Act
        register_tool_formatter(tool_name, mock_schema_formatter, mock_example_formatter)
        
        # Assert
        # 1. Registry singleton was retrieved
        MockRegistry.assert_called()
        
        # 2. register_tool_formatter was called on the instance
        mock_registry_instance.register_tool_formatter.assert_called_once()
        
        # 3. Verify arguments (tool name and a ToolFormatterPair)
        args, _ = mock_registry_instance.register_tool_formatter.call_args
        assert args[0] == tool_name
        
        registered_pair = args[1]
        assert registered_pair.schema_formatter == mock_schema_formatter
        assert registered_pair.example_formatter == mock_example_formatter
