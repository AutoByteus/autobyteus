# file: autobyteus/tests/unit_tests/agent/llm_response_processor/registries/test_xml_response_processor_registry.py
import pytest

from autobyteus.llm.providers import LLMProvider
from autobyteus.agent.llm_response_processor.registries import XmlResponseProcessorRegistry
from autobyteus.agent.llm_response_processor.default_xml_tool_usage_processor import DefaultXmlToolUsageProcessor
from autobyteus.agent.llm_response_processor.anthropic_xml_tool_usage_processor import AnthropicXmlToolUsageProcessor

def test_xml_registry_returns_anthropic_processor():
    """Verify registry returns the specific processor for Anthropic."""
    registry = XmlResponseProcessorRegistry()
    processor = registry.get_processor(LLMProvider.ANTHROPIC)
    assert isinstance(processor, AnthropicXmlToolUsageProcessor)

def test_xml_registry_returns_default_for_unmapped_provider():
    """Verify registry returns the default processor for a provider not in its map."""
    registry = XmlResponseProcessorRegistry()
    processor = registry.get_processor(LLMProvider.OPENAI) # A non-XML provider
    assert isinstance(processor, DefaultXmlToolUsageProcessor)

def test_xml_registry_returns_default_for_none_provider():
    """Verify registry returns the default when no provider is specified."""
    registry = XmlResponseProcessorRegistry()
    processor = registry.get_processor(None)
    assert isinstance(processor, DefaultXmlToolUsageProcessor)
