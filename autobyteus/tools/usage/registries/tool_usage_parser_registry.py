# file: autobyteus/autobyteus/tools/usage/registries/tool_usage_parser_registry.py
import logging
from typing import Dict, Optional

from autobyteus.llm.providers import LLMProvider
from autobyteus.utils.singleton import SingletonMeta
from autobyteus.tools.usage.parsers import (
    BaseToolUsageParser,
    DefaultJsonToolUsageParser,
    OpenAiJsonToolUsageParser,
    GeminiJsonToolUsageParser,
    DefaultXmlToolUsageParser
)

logger = logging.getLogger(__name__)

class ToolUsageParserRegistry(metaclass=SingletonMeta):
    """
    A consolidated registry that maps an LLMProvider directly to its required
    tool usage parser, encapsulating the logic of which provider uses which format.
    """

    def __init__(self):
        self._parsers: Dict[LLMProvider, BaseToolUsageParser] = {
            # JSON-based providers
            LLMProvider.OPENAI: OpenAiJsonToolUsageParser(),
            LLMProvider.MISTRAL: OpenAiJsonToolUsageParser(),
            LLMProvider.DEEPSEEK: OpenAiJsonToolUsageParser(),
            LLMProvider.GROK: OpenAiJsonToolUsageParser(),
            LLMProvider.GEMINI: GeminiJsonToolUsageParser(),
            
            # XML-based providers
            LLMProvider.ANTHROPIC: DefaultXmlToolUsageParser(),
        }
        # A default parser for any provider not explicitly listed (defaults to JSON)
        self._default_parser = DefaultJsonToolUsageParser()
        logger.info("ToolUsageParserRegistry initialized with direct provider-to-parser mappings.")

    def get_parser(self, provider: Optional[LLMProvider]) -> BaseToolUsageParser:
        """
        Retrieves the appropriate tool usage parser for a given provider.

        Args:
            provider: The LLMProvider enum member.

        Returns:
            The corresponding BaseToolUsageParser instance.
        """
        if provider and provider in self._parsers:
            parser = self._parsers[provider]
            logger.debug(f"Found specific tool usage parser for provider {provider.name}: {parser.get_name()}")
            return parser
        
        logger.debug(f"No specific tool usage parser for provider {provider.name if provider else 'Unknown'}. Returning default parser.")
        return self._default_parser
