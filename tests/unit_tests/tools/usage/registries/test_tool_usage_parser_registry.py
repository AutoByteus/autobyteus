# file: autobyteus/tests/unit_tests/tools/usage/registries/test_tool_usage_parser_registry.py
import pytest
from autobyteus.tools.usage.registries.tool_usage_parser_registry import ToolUsageParserRegistry
from autobyteus.llm.providers import LLMProvider
from autobyteus.tools.usage.parsers import (
    OpenAiJsonToolUsageParser,
    DefaultXmlToolUsageParser,
    DefaultJsonToolUsageParser
)

@pytest.fixture
def registry():
    return ToolUsageParserRegistry()

def test_get_openai_parser(registry: ToolUsageParserRegistry):
    parser = registry.get_parser(LLMProvider.OPENAI)
    assert isinstance(parser, OpenAiJsonToolUsageParser)

def test_get_anthropic_parser(registry: ToolUsageParserRegistry):
    parser = registry.get_parser(LLMProvider.ANTHROPIC)
    assert isinstance(parser, DefaultXmlToolUsageParser)

def test_get_default_parser_for_unregistered_provider(registry: ToolUsageParserRegistry):
    # Kimi is not explicitly in the map, so it should get the default JSON parser
    parser = registry.get_parser(LLMProvider.KIMI)
    assert isinstance(parser, DefaultJsonToolUsageParser)

def test_get_default_parser_for_none_provider(registry: ToolUsageParserRegistry):
    parser = registry.get_parser(None)
    assert isinstance(parser, DefaultJsonToolUsageParser)
