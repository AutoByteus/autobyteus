# file: autobyteus/autobyteus/agent/llm_response_processor/__init__.py
"""
Components for processing LLM responses, primarily for extracting tool invocations
or other structured commands.
"""
from .base_processor import BaseLLMResponseProcessor

# Import concrete processors to make them easily accessible for instantiation
from .xml_tool_usage_processor import XmlToolUsageProcessor
from .json_tool_usage_processor import JsonToolUsageProcessor

__all__ = [
    "BaseLLMResponseProcessor",
    "XmlToolUsageProcessor",
    "JsonToolUsageProcessor",
]
