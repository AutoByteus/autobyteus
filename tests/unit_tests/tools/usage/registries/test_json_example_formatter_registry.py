# file: autobyteus/tests/unit_tests/tools/usage/registries/test_json_example_formatter_registry.py
import pytest
from autobyteus.tools.usage.registries.json_example_formatter_registry import JsonExampleFormatterRegistry
from autobyteus.llm.providers import LLMProvider
from autobyteus.tools.usage.formatters import (
    OpenAiJsonExampleFormatter,
    AnthropicJsonExampleFormatter,
    GeminiJsonExampleFormatter,
    DefaultJsonExampleFormatter
)

@pytest.fixture
def registry():
    return JsonExampleFormatterRegistry()

def test_get_openai_example_formatter(registry: JsonExampleFormatterRegistry):
    formatter = registry.get_formatter(LLMProvider.OPENAI)
    assert isinstance(formatter, OpenAiJsonExampleFormatter)

def test_get_anthropic_example_formatter(registry: JsonExampleFormatterRegistry):
    formatter = registry.get_formatter(LLMProvider.ANTHROPIC)
    assert isinstance(formatter, AnthropicJsonExampleFormatter)

def test_get_gemini_example_formatter(registry: JsonExampleFormatterRegistry):
    formatter = registry.get_formatter(LLMProvider.GEMINI)
    assert isinstance(formatter, GeminiJsonExampleFormatter)

def test_get_default_formatter_for_unregistered_provider(registry: JsonExampleFormatterRegistry):
    formatter = registry.get_formatter(LLMProvider.OLLAMA) 
    assert isinstance(formatter, DefaultJsonExampleFormatter)

def test_get_default_formatter_explicitly(registry: JsonExampleFormatterRegistry):
    formatter = registry.get_default_formatter()
    assert isinstance(formatter, DefaultJsonExampleFormatter)
