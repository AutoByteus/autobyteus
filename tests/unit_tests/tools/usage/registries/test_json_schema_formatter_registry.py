# file: autobyteus/tests/unit_tests/tools/usage/registries/test_json_schema_formatter_registry.py
import pytest
from autobyteus.tools.usage.registries.json_schema_formatter_registry import JsonSchemaFormatterRegistry
from autobyteus.llm.providers import LLMProvider
from autobyteus.tools.usage.formatters import (
    OpenAiJsonSchemaFormatter,
    AnthropicJsonSchemaFormatter,
    GeminiJsonSchemaFormatter,
    DefaultJsonSchemaFormatter
)

@pytest.fixture
def registry():
    return JsonSchemaFormatterRegistry()

def test_get_openai_formatter(registry: JsonSchemaFormatterRegistry):
    formatter = registry.get_formatter(LLMProvider.OPENAI)
    assert isinstance(formatter, OpenAiJsonSchemaFormatter)

def test_get_anthropic_formatter(registry: JsonSchemaFormatterRegistry):
    formatter = registry.get_formatter(LLMProvider.ANTHROPIC)
    assert isinstance(formatter, AnthropicJsonSchemaFormatter)

def test_get_gemini_formatter(registry: JsonSchemaFormatterRegistry):
    formatter = registry.get_formatter(LLMProvider.GEMINI)
    assert isinstance(formatter, GeminiJsonSchemaFormatter)

def test_get_default_formatter_for_unregistered_provider(registry: JsonSchemaFormatterRegistry):
    # This provider is not specifically mapped, so it should fall back to the default
    formatter = registry.get_formatter(LLMProvider.OLLAMA) 
    assert isinstance(formatter, DefaultJsonSchemaFormatter)

def test_get_default_formatter_explicitly(registry: JsonSchemaFormatterRegistry):
    formatter = registry.get_default_formatter()
    assert isinstance(formatter, DefaultJsonSchemaFormatter)
