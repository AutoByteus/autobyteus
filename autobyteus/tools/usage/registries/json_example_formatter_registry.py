# file: autobyteus/autobyteus/tools/usage/registries/json_example_formatter_registry.py
import logging
from typing import Dict

from autobyteus.llm.providers import LLMProvider
from autobyteus.tools.usage.formatters.base_formatter import BaseExampleFormatter
from autobyteus.tools.usage.formatters.default_json_example_formatter import DefaultJsonExampleFormatter
from autobyteus.tools.usage.formatters.openai_json_example_formatter import OpenAiJsonExampleFormatter
from autobyteus.tools.usage.formatters.anthropic_json_example_formatter import AnthropicJsonExampleFormatter
from autobyteus.tools.usage.formatters.gemini_json_example_formatter import GeminiJsonExampleFormatter
from autobyteus.utils.singleton import SingletonMeta

logger = logging.getLogger(__name__)

class JsonExampleFormatterRegistry(metaclass=SingletonMeta):
    """A singleton registry for retrieving JSON example formatters based on LLM provider."""

    def __init__(self):
        self._formatters: Dict[LLMProvider, BaseExampleFormatter] = {
            LLMProvider.OPENAI: OpenAiJsonExampleFormatter(),
            LLMProvider.MISTRAL: OpenAiJsonExampleFormatter(),
            LLMProvider.DEEPSEEK: OpenAiJsonExampleFormatter(),
            LLMProvider.GROK: OpenAiJsonExampleFormatter(),
            LLMProvider.ANTHROPIC: AnthropicJsonExampleFormatter(),
            LLMProvider.GEMINI: GeminiJsonExampleFormatter(),
        }
        self._default_formatter = DefaultJsonExampleFormatter()
        logger.info("JsonExampleFormatterRegistry initialized.")

    def get_formatter(self, provider: LLMProvider) -> BaseExampleFormatter:
        """
        Retrieves the appropriate example formatter for a given LLM provider.

        Args:
            provider: The LLMProvider enum member.

        Returns:
            An instance of a class derived from BaseExampleFormatter.
        """
        formatter = self._formatters.get(provider)
        if formatter:
            logger.debug(f"Found specific example formatter for provider {provider.name}: {formatter.__class__.__name__}")
            return formatter
        
        logger.debug(f"No specific example formatter for provider {provider.name}. "
                     f"Returning default: {self._default_formatter.__class__.__name__}")
        return self._default_formatter
    
    def get_default_formatter(self) -> BaseExampleFormatter:
        """Explicitly returns the default formatter."""
        return self._default_formatter
