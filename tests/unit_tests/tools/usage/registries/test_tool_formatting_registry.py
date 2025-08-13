# file: autobyteus/tests/unit_tests/tools/usage/registries/test_tool_formatting_registry.py
import pytest
from autobyteus.tools.usage.registries.tool_formatting_registry import ToolFormattingRegistry
from autobyteus.llm.providers import LLMProvider
from autobyteus.tools.usage.formatters import (
    OpenAiJsonSchemaFormatter, OpenAiJsonExampleFormatter,
    DefaultXmlSchemaFormatter, DefaultXmlExampleFormatter,
    DefaultJsonSchemaFormatter, DefaultJsonExampleFormatter
)
from autobyteus.tools.usage.registries.tool_formatter_pair import ToolFormatterPair

@pytest.fixture
def registry():
    # Use a new instance for each test to avoid singleton state issues
    return ToolFormattingRegistry()

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
    # Kimi is not explicitly in the map, so it should get the default JSON pair
    pair = registry.get_formatter_pair(LLMProvider.KIMI)
    assert isinstance(pair, ToolFormatterPair)
    assert isinstance(pair.schema_formatter, DefaultJsonSchemaFormatter)
    assert isinstance(pair.example_formatter, DefaultJsonExampleFormatter)

def test_get_default_pair_for_none_provider(registry: ToolFormattingRegistry):
    pair = registry.get_formatter_pair(None)
    assert isinstance(pair, ToolFormatterPair)
    assert isinstance(pair.schema_formatter, DefaultJsonSchemaFormatter)
    assert isinstance(pair.example_formatter, DefaultJsonExampleFormatter)
