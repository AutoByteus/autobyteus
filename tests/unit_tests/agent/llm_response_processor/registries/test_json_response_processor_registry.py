# file: autobyteus/tests/unit_tests/agent/llm_response_processor/registries/test_json_response_processor_registry.py
import pytest

from autobyteus.llm.providers import LLMProvider
from autobyteus.agent.llm_response_processor.registries import JsonResponseProcessorRegistry
from autobyteus.agent.llm_response_processor.default_json_tool_usage_processor import DefaultJsonToolUsageProcessor
from autobyteus.agent.llm_response_processor.openai_json_tool_usage_processor import OpenAiJsonToolUsageProcessor
from autobyteus.agent.llm_response_processor.gemini_json_tool_usage_processor import GeminiJsonToolUsageProcessor

@pytest.mark.parametrize("provider", [
    LLMProvider.OPENAI,
    LLMProvider.MISTRAL,
    LLMProvider.DEEPSEEK,
    LLMProvider.GROK
])
def test_json_registry_returns_openai_processor_for_compatibles(provider):
    """Verify registry returns the OpenAI processor for all compatible providers."""
    registry = JsonResponseProcessorRegistry()
    processor = registry.get_processor(provider)
    assert isinstance(processor, OpenAiJsonToolUsageProcessor)

def test_json_registry_returns_gemini_processor():
    """Verify registry returns the specific processor for Gemini."""
    registry = JsonResponseProcessorRegistry()
    processor = registry.get_processor(LLMProvider.GEMINI)
    assert isinstance(processor, GeminiJsonToolUsageProcessor)

def test_json_registry_returns_default_for_unmapped_provider():
    """Verify registry returns the default for a provider not in its JSON map."""
    registry = JsonResponseProcessorRegistry()
    processor = registry.get_processor(LLMProvider.ANTHROPIC) # An XML provider
    assert isinstance(processor, DefaultJsonToolUsageProcessor)

def test_json_registry_returns_default_for_none_provider():
    """Verify registry returns the default when no provider is specified."""
    registry = JsonResponseProcessorRegistry()
    processor = registry.get_processor(None)
    assert isinstance(processor, DefaultJsonToolUsageProcessor)
