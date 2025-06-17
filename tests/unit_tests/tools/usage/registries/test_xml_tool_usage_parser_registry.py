# file: autobyteus/tests/unit_tests/tools/usage/registries/test_xml_tool_usage_parser_registry.py
import pytest
from autobyteus.tools.usage.registries import XmlToolUsageParserRegistry
from autobyteus.llm.providers import LLMProvider
from autobyteus.tools.usage.parsers import DefaultXmlToolUsageParser

@pytest.fixture
def registry():
    return XmlToolUsageParserRegistry()

def test_get_parser_always_returns_default(registry: XmlToolUsageParserRegistry):
    # Test with a specific provider
    parser_openai = registry.get_parser(LLMProvider.OPENAI)
    assert isinstance(parser_openai, DefaultXmlToolUsageParser)

    # Test with no provider
    parser_none = registry.get_parser()
    assert isinstance(parser_none, DefaultXmlToolUsageParser)

    assert parser_openai is parser_none
