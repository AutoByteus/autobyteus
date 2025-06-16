# file: autobyteus/autobyteus/agent/llm_response_processor/registries/__init__.py
"""
Contains registries for mapping LLM providers to specific response processors.
"""
from .xml_response_processor_registry import XmlResponseProcessorRegistry
from .json_response_processor_registry import JsonResponseProcessorRegistry

__all__ = [
    "XmlResponseProcessorRegistry",
    "JsonResponseProcessorRegistry",
]
