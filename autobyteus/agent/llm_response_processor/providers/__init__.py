# file: autobyteus/autobyteus/agent/llm_response_processor/providers/__init__.py
"""
Contains high-level providers for retrieving the correct response processor
based on the desired format (XML or JSON).
"""
from .xml_response_processor_provider import XmlResponseProcessorProvider
from .json_response_processor_provider import JsonResponseProcessorProvider

__all__ = [
    "XmlResponseProcessorProvider",
    "JsonResponseProcessorProvider",
]
