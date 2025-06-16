# file: autobyteus/autobyteus/agent/llm_response_processor/registries/json_response_processor_registry.py
import logging
from typing import Dict, Optional

from autobyteus.llm.providers import LLMProvider
from autobyteus.utils.singleton import SingletonMeta
from ..base_processor import BaseLLMResponseProcessor
from ..default_json_tool_usage_processor import DefaultJsonToolUsageProcessor
from ..openai_json_tool_usage_processor import OpenAiJsonToolUsageProcessor
from ..gemini_json_tool_usage_processor import GeminiJsonToolUsageProcessor

logger = logging.getLogger(__name__)

class JsonResponseProcessorRegistry(metaclass=SingletonMeta):
    """A singleton registry for retrieving JSON-based LLM response processors."""

    def __init__(self):
        self._processors: Dict[LLMProvider, BaseLLMResponseProcessor] = {
            LLMProvider.OPENAI: OpenAiJsonToolUsageProcessor(),
            LLMProvider.MISTRAL: OpenAiJsonToolUsageProcessor(),
            LLMProvider.DEEPSEEK: OpenAiJsonToolUsageProcessor(),
            LLMProvider.GROK: OpenAiJsonToolUsageProcessor(),
            LLMProvider.GEMINI: GeminiJsonToolUsageProcessor(),
        }
        self._default_processor = DefaultJsonToolUsageProcessor()
        logger.info("JsonResponseProcessorRegistry initialized.")

    def get_processor(self, provider: Optional[LLMProvider] = None) -> BaseLLMResponseProcessor:
        """
        Retrieves the appropriate JSON response processor for a given LLM provider.
        If no specific processor is found, returns the default JSON processor.
        """
        if provider:
            processor = self._processors.get(provider)
            if processor:
                logger.debug(f"Found specific JSON response processor for provider {provider.name}: {processor.__class__.__name__}")
                return processor
        
        logger.debug(f"Returning default JSON response processor: {self._default_processor.__class__.__name__}")
        return self._default_processor
