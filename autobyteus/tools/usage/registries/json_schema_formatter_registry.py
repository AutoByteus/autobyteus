# file: autobyteus/autobyteus/tools/usage/registries/json_schema_formatter_registry.py
import logging
from typing import Dict

from autobyteus.llm.providers import LLMProvider
from autobyteus.tools.usage.formatters.base_formatter import BaseSchemaFormatter
from autobyteus.tools.usage.formatters.default_json_schema_formatter import DefaultJsonSchemaFormatter
from autobyteus.tools.usage.formatters.openai_json_schema_formatter import OpenAiJsonSchemaFormatter
from autobyteus.tools.usage.formatters.anthropic_json_schema_formatter import AnthropicJsonSchemaFormatter
from autobyteus.tools.usage.formatters.gemini_json_schema_formatter import GeminiJsonSchemaFormatter
from autobyteus.utils.singleton import SingletonMeta

logger = logging.getLogger(__name__)

class JsonSchemaFormatterRegistry(metaclass=SingletonMeta):
    """A singleton registry for retrieving JSON schema formatters based on LLM provider."""

    def __init__(self):
        self._formatters: Dict[LLMProvider, BaseSchemaFormatter] = {
            LLMProvider.OPENAI: OpenAiJsonSchemaFormatter(),
            LLMProvider.MISTRAL: OpenAiJsonSchemaFormatter(),
            LLMProvider.DEEPSEEK: OpenAiJsonSchemaFormatter(),
            LLMProvider.GROK: OpenAiJsonSchemaFormatter(),
            LLMProvider.ANTHROPIC: AnthropicJsonSchemaFormatter(),
            LLMProvider.GEMINI: GeminiJsonSchemaFormatter(),
        }
        self._default_formatter = DefaultJsonSchemaFormatter()
        logger.info("JsonSchemaFormatterRegistry initialized.")

    def get_formatter(self, provider: LLMProvider) -> BaseSchemaFormatter:
        """
        Retrieves the appropriate schema formatter for a given LLM provider.

        Args:
            provider: The LLMProvider enum member.

        Returns:
            An instance of a class derived from BaseSchemaFormatter.
        """
        formatter = self._formatters.get(provider)
        if formatter:
            logger.debug(f"Found specific schema formatter for provider {provider.name}: {formatter.__class__.__name__}")
            return formatter

        logger.debug(f"No specific schema formatter for provider {provider.name}. "
                     f"Returning default: {self._default_formatter.__class__.__name__}")
        return self._default_formatter

    def get_default_formatter(self) -> BaseSchemaFormatter:
        """Explicitly returns the default formatter."""
        return self._default_formatter
