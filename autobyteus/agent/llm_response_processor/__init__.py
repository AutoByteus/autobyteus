# file: autobyteus/autobyteus/agent/llm_response_processor/__init__.py
"""
Components for processing LLM responses, primarily for extracting tool invocations.
This package follows a provider-registry pattern for selecting the correct processor.
"""
from .base_processor import BaseLLMResponseProcessor
from .provider_aware_tool_usage_processor import ProviderAwareToolUsageProcessor

# The main entry point is the ProviderAwareToolUsageProcessor.
# Other components can be imported for extension or direct use if needed.
from .providers import XmlResponseProcessorProvider, JsonResponseProcessorProvider
from .registries import XmlResponseProcessorRegistry, JsonResponseProcessorRegistry
from .default_xml_tool_usage_processor import DefaultXmlToolUsageProcessor
from .default_json_tool_usage_processor import DefaultJsonToolUsageProcessor
from .openai_json_tool_usage_processor import OpenAiJsonToolUsageProcessor
from .gemini_json_tool_usage_processor import GeminiJsonToolUsageProcessor
from .anthropic_xml_tool_usage_processor import AnthropicXmlToolUsageProcessor

__all__ = [
    # Primary public classes
    "BaseLLMResponseProcessor",
    "ProviderAwareToolUsageProcessor",

    # Lower-level components
    "XmlResponseProcessorProvider",
    "JsonResponseProcessorProvider",
    "XmlResponseProcessorRegistry",
    "JsonResponseProcessorRegistry",
    "DefaultXmlToolUsageProcessor",
    "DefaultJsonToolUsageProcessor",
    "OpenAiJsonToolUsageProcessor",
    "GeminiJsonToolUsageProcessor",
    "AnthropicXmlToolUsageProcessor"
]
