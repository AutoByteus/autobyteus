# file: autobyteus/autobyteus/tools/usage/providers/xml_tool_usage_parser_provider.py
from typing import Optional, TYPE_CHECKING

from autobyteus.llm.providers import LLMProvider
from autobyteus.tools.usage.registries.xml_tool_usage_parser_registry import XmlToolUsageParserRegistry

if TYPE_CHECKING:
    from autobyteus.tools.usage.parsers.base_parser import BaseToolUsageParser

class XmlToolUsageParserProvider:
    """Provides a tool usage parser for XML-based responses."""

    def __init__(self):
        self._registry = XmlToolUsageParserRegistry()

    def provide(self, llm_provider: Optional[LLMProvider] = None) -> 'BaseToolUsageParser':
        """
        Gets the appropriate parser from the registry.

        Args:
            llm_provider: Ignored, for API consistency.

        Returns:
            An instance of a class derived from BaseToolUsageParser.
        """
        return self._registry.get_parser(llm_provider)
