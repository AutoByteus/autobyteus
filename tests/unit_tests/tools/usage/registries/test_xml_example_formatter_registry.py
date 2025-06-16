# file: autobyteus/tests/unit_tests/tools/usage/registries/test_xml_example_formatter_registry.py
import pytest
from autobyteus.tools.usage.registries.xml_example_formatter_registry import XmlExampleFormatterRegistry
from autobyteus.llm.providers import LLMProvider
from autobyteus.tools.usage.formatters import DefaultXmlExampleFormatter

@pytest.fixture
def registry():
    return XmlExampleFormatterRegistry()

def test_get_formatter_always_returns_default(registry: XmlExampleFormatterRegistry):
    """
    Tests that the XML example registry always returns the default formatter.
    """
    formatter_openai = registry.get_formatter(LLMProvider.OPENAI)
    assert isinstance(formatter_openai, DefaultXmlExampleFormatter)

    formatter_none = registry.get_formatter()
    assert isinstance(formatter_none, DefaultXmlExampleFormatter)

    assert formatter_openai is formatter_none
