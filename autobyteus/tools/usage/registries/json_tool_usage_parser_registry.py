# file: autobyteus/autobyteus/tools/usage/registries/json_tool_usage_parser_registry.py
import logging
from typing import Dict

from autobyteus.llm.providers import LLMProvider
from autobyteus.tools.usage.parsers.base_parser import BaseToolUsageParser
from autobyteus.tools.usage.parsers.default_json_tool_usage_parser import DefaultJsonToolUsageParser
from autobyteus.tools.usage.parsers.openai_json_tool_usage_parser import OpenAiJsonToolUsageParser
from autobyteus.tools.usage.parsers.gemini_json_tool_usage_parser import GeminiJsonToolUsageParser
from autobyteus.utils.singleton import SingletonMeta

logger = logging.getLogger(__name__)

class JsonToolUsageParserRegistry(metaclass=SingletonMeta):
    """A singleton registry for retrieving JSON-based tool usage parsers."""

    def __init__(self):
        self._parsers: Dict[LLMProvider, BaseToolUsageParser] = {
            LLMProvider.OPENAI: OpenAiJsonToolUsageParser(),
            LLMProvider.MISTRAL: OpenAiJsonToolUsageParser(),
            LLMProvider.DEEPSEEK: OpenAiJsonToolUsageParser(),
            LLMProvider.GROK: OpenAiJsonToolUsageParser(),
            LLMProvider.GEMINI: GeminiJsonToolUsageParser(),
        }
        self._default_parser = DefaultJsonToolUsageParser()
        logger.info("JsonToolUsageParserRegistry initialized.")

    def get_parser(self, provider: LLMProvider) -> BaseToolUsageParser:
        """
        Retrieves the appropriate parser for a given LLM provider.
        """
        parser = self._parsers.get(provider)
        if parser:
            logger.debug(f"Found specific tool usage parser for provider {provider.name}: {parser.get_name()}")
            return parser
        
        logger.debug(f"No specific tool usage parser for provider {provider.name}. Returning default: {self._default_parser.get_name()}")
        return self._default_parser
    
    def get_default_parser(self) -> BaseToolUsageParser:
        """Explicitly returns the default parser."""
        return self._default_parser
