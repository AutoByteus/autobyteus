# file: autobyteus/tests/unit_tests/tools/usage/registries/test_json_tool_usage_parser_registry.py
import pytest
from autobyteus.tools.usage.registries import JsonToolUsageParserRegistry
from autobyteus.llm.providers import LLMProvider
from autobyteus.tools.usage.parsers import (
    OpenAiJsonToolUsageParser,
    GeminiJsonToolUsageParser,
    DefaultJsonToolUsageParser,
)

@pytest.fixture
def registry():
    return JsonToolUsageParserRegistry()

def test_get_openai_parser(registry: JsonToolUsageParserRegistry):
    parser = registry.get_parser(LLMProvider.OPENAI)
    assert isinstance(parser, OpenAiJsonToolUsageParser)

def test_get_gemini_parser(registry: JsonToolUsageParserRegistry):
    parser = registry.get_parser(LLMProvider.GEMINI)
    assert isinstance(parser, GeminiJsonToolUsageParser)

def test_get_default_parser_for_unregistered_provider(registry: JsonToolUsageParserRegistry):
    parser = registry.get_parser(LLMProvider.ANTHROPIC) 
    assert isinstance(parser, DefaultJsonToolUsageParser)

def test_get_default_parser_explicitly(registry: JsonToolUsageParserRegistry):
    parser = registry.get_default_parser()
    assert isinstance(parser, DefaultJsonToolUsageParser)
