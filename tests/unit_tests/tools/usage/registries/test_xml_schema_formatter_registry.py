# file: autobyteus/tests/unit_tests/tools/usage/registries/test_xml_schema_formatter_registry.py
import pytest
from autobyteus.tools.usage.registries.xml_schema_formatter_registry import XmlSchemaFormatterRegistry
from autobyteus.llm.providers import LLMProvider
from autobyteus.tools.usage.formatters import DefaultXmlSchemaFormatter

@pytest.fixture
def registry():
    return XmlSchemaFormatterRegistry()

def test_get_formatter_always_returns_default(registry: XmlSchemaFormatterRegistry):
    """
    Tests that the XML registry always returns the default formatter, regardless of provider.
    """
    # Test with a specific provider
    formatter_openai = registry.get_formatter(LLMProvider.OPENAI)
    assert isinstance(formatter_openai, DefaultXmlSchemaFormatter)

    # Test with no provider
    formatter_none = registry.get_formatter()
    assert isinstance(formatter_none, DefaultXmlSchemaFormatter)

    # Test with another provider
    formatter_anthropic = registry.get_formatter(LLMProvider.ANTHROPIC)
    assert isinstance(formatter_anthropic, DefaultXmlSchemaFormatter)

    assert formatter_openai is formatter_none is formatter_anthropic
