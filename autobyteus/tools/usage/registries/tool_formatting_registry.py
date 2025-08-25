# file: autobyteus/autobyteus/tools/usage/registries/tool_formatting_registry.py
import logging
from typing import Dict, Optional

from autobyteus.llm.providers import LLMProvider
from autobyteus.utils.singleton import SingletonMeta
from .tool_formatter_pair import ToolFormatterPair

# Import all necessary formatters
from autobyteus.tools.usage.formatters import (
    DefaultJsonSchemaFormatter, OpenAiJsonSchemaFormatter, AnthropicJsonSchemaFormatter, GeminiJsonSchemaFormatter,
    DefaultJsonExampleFormatter, OpenAiJsonExampleFormatter, AnthropicJsonExampleFormatter, GeminiJsonExampleFormatter,
    DefaultXmlSchemaFormatter, DefaultXmlExampleFormatter
)

logger = logging.getLogger(__name__)

class ToolFormattingRegistry(metaclass=SingletonMeta):
    """
    A consolidated registry that maps an LLMProvider directly to its required
    ToolFormatterPair, which contains both schema and example formatters.
    """

    def __init__(self):
        # A single, direct mapping from provider to its correct formatter pair.
        self._pairs: Dict[LLMProvider, ToolFormatterPair] = {
            # JSON-based providers
            LLMProvider.OPENAI: ToolFormatterPair(OpenAiJsonSchemaFormatter(), OpenAiJsonExampleFormatter()),
            LLMProvider.MISTRAL: ToolFormatterPair(OpenAiJsonSchemaFormatter(), OpenAiJsonExampleFormatter()),
            LLMProvider.DEEPSEEK: ToolFormatterPair(OpenAiJsonSchemaFormatter(), OpenAiJsonExampleFormatter()),
            LLMProvider.GROK: ToolFormatterPair(OpenAiJsonSchemaFormatter(), OpenAiJsonExampleFormatter()),
            LLMProvider.GEMINI: ToolFormatterPair(GeminiJsonSchemaFormatter(), GeminiJsonExampleFormatter()),
            
            # XML-based providers
            LLMProvider.ANTHROPIC: ToolFormatterPair(DefaultXmlSchemaFormatter(), DefaultXmlExampleFormatter()),
        }
        # A default pair for any provider not explicitly listed (defaults to JSON)
        self._default_pair = ToolFormatterPair(DefaultJsonSchemaFormatter(), DefaultJsonExampleFormatter())
        # A specific pair for the XML override
        self._xml_override_pair = ToolFormatterPair(DefaultXmlSchemaFormatter(), DefaultXmlExampleFormatter())
        
        logger.info("ToolFormattingRegistry initialized with direct provider-to-formatter mappings.")

    def get_formatter_pair(self, provider: Optional[LLMProvider], use_xml_tool_format: bool = False) -> ToolFormatterPair:
        """
        Retrieves the appropriate formatting pair for a given provider, honoring the XML override.

        Args:
            provider: The LLMProvider enum member.
            use_xml_tool_format: If True, forces the use of XML formatters.

        Returns:
            The corresponding ToolFormatterPair instance.
        """
        if use_xml_tool_format:
            logger.debug("XML tool format is forced by configuration. Returning XML formatter pair.")
            return self._xml_override_pair

        if provider and provider in self._pairs:
            pair = self._pairs[provider]
            logger.debug(f"Found specific formatter pair for provider {provider.name}: {pair}")
            return pair
        
        logger.debug(f"No specific formatter pair for provider {provider.name if provider else 'Unknown'}. Returning default pair.")
        return self._default_pair
