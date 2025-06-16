# file: autobyteus/autobyteus/agent/llm_response_processor/registries/xml_response_processor_registry.py
import logging
from typing import Dict, Optional

from autobyteus.llm.providers import LLMProvider
from autobyteus.utils.singleton import SingletonMeta
from ..base_processor import BaseLLMResponseProcessor
from ..default_xml_tool_usage_processor import DefaultXmlToolUsageProcessor
from ..anthropic_xml_tool_usage_processor import AnthropicXmlToolUsageProcessor

logger = logging.getLogger(__name__)

class XmlResponseProcessorRegistry(metaclass=SingletonMeta):
    """A singleton registry for retrieving XML-based LLM response processors."""

    def __init__(self):
        self._processors: Dict[LLMProvider, BaseLLMResponseProcessor] = {
            LLMProvider.ANTHROPIC: AnthropicXmlToolUsageProcessor(),
        }
        self._default_processor = DefaultXmlToolUsageProcessor()
        logger.info("XmlResponseProcessorRegistry initialized.")

    def get_processor(self, provider: Optional[LLMProvider] = None) -> BaseLLMResponseProcessor:
        """
        Retrieves the appropriate XML response processor for a given LLM provider.
        If no specific processor is found, returns the default XML processor.
        """
        if provider:
            processor = self._processors.get(provider)
            if processor:
                logger.debug(f"Found specific XML response processor for provider {provider.name}: {processor.__class__.__name__}")
                return processor
        
        logger.debug(f"Returning default XML response processor: {self._default_processor.__class__.__name__}")
        return self._default_processor
