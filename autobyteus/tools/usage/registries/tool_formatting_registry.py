# file: autobyteus/autobyteus/tools/usage/registries/tool_formatting_registry.py
import logging
from typing import Dict, Optional

from autobyteus.llm.providers import LLMProvider
from autobyteus.utils.singleton import SingletonMeta
from .tool_formatter_pair import ToolFormatterPair
from autobyteus.utils.tool_call_format import resolve_tool_call_format

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

    def get_formatter_pair(self, provider: Optional[LLMProvider]) -> ToolFormatterPair:
        """
        Retrieves the appropriate formatting pair for a given provider, honoring the env format override.

        Args:
            provider: The LLMProvider enum member.

        Returns:
            The corresponding ToolFormatterPair instance.
        """
        format_override = resolve_tool_call_format()
        if format_override == "xml":
            logger.debug("XML tool format is forced by environment. Returning XML formatter pair.")
            return self._xml_override_pair
        if format_override == "json":
            logger.debug("JSON tool format is forced by environment. Returning JSON formatter pair.")
            return self._default_pair
        if format_override in {"sentinel", "native"}:
            logger.debug(
                "Tool format '%s' is not supported by formatter registry. "
                "Falling back to JSON formatters.",
                format_override,
            )
            return self._default_pair

        if provider and provider in self._pairs:
            pair = self._pairs[provider]
            logger.debug(f"Found specific formatter pair for provider {provider.name}: {pair}")
            return pair
        
        logger.debug(f"No specific formatter pair for provider {provider.name if provider else 'Unknown'}. Returning default pair.")
        return self._default_pair
