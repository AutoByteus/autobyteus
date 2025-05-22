# file: autobyteus/autobyteus/agent/llm_response_processor/__init__.py
"""
Components for processing LLM responses, primarily for extracting tool invocations
or other structured commands. Includes auto-registration mechanisms.
"""
from .processor_definition import LLMResponseProcessorDefinition
from .processor_registry import LLMResponseProcessorRegistry, default_llm_response_processor_registry
from .processor_meta import LLMResponseProcessorMeta
from .base_processor import BaseLLMResponseProcessor

# Import processors from their individual files to ensure they are registered by the metaclass
from .xml_tool_usage_processor import XmlToolUsageProcessor
from .json_tool_usage_processor import JsonToolUsageProcessor

__all__ = [
    "LLMResponseProcessorDefinition",
    "LLMResponseProcessorRegistry",
    "default_llm_response_processor_registry",
    "LLMResponseProcessorMeta",
    "BaseLLMResponseProcessor",
    "XmlToolUsageProcessor",
    "JsonToolUsageProcessor",
]
