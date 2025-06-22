# file: autobyteus/autobyteus/tools/usage/providers/json_tool_usage_parser_provider.py
from typing import Optional, TYPE_CHECKING

from autobyteus.llm.providers import LLMProvider
from autobyteus.tools.usage.registries.json_tool_usage_parser_registry import JsonToolUsageParserRegistry

if TYPE_CHECKING:
    from autobyteus.tools.usage.parsers.base_parser import BaseToolUsageParser

class JsonToolUsageParserProvider:
    """Provides a tool usage parser for JSON-based responses, specific to an LLM provider."""

    def __init__(self):
        self._registry = JsonToolUsageParserRegistry()

    def provide(self, llm_provider: Optional[LLMProvider] = None) -> 'BaseToolUsageParser':
        """
        Gets the appropriate parser from the registry.

        Args:
            llm_provider: The LLMProvider for which to get a parser.

        Returns:
            An instance of a class derived from BaseToolUsageParser.
        """
        if llm_provider:
            return self._registry.get_parser(llm_provider)
        return self._registry.get_default_parser()
