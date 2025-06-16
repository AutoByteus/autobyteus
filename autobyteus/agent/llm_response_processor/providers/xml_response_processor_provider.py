# file: autobyteus/autobyteus/agent/llm_response_processor/providers/xml_response_processor_provider.py
from typing import Optional

from autobyteus.llm.providers import LLMProvider
from ..registries.xml_response_processor_registry import XmlResponseProcessorRegistry
from ..base_processor import BaseLLMResponseProcessor

class XmlResponseProcessorProvider:
    """Provides the correct XML response processor for a given LLM provider by using a registry."""
    def __init__(self):
        self._registry = XmlResponseProcessorRegistry()

    def get_processor(self, provider: Optional[LLMProvider] = None) -> BaseLLMResponseProcessor:
        """Gets the processor from the registry."""
        return self._registry.get_processor(provider)
