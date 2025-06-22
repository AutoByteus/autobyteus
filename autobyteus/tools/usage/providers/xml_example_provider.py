# file: autobyteus/autobyteus/tools/usage/providers/xml_example_provider.py
from typing import Optional, TYPE_CHECKING

from autobyteus.llm.providers import LLMProvider
from autobyteus.tools.usage.registries.xml_example_formatter_registry import XmlExampleFormatterRegistry

if TYPE_CHECKING:
    from autobyteus.tools.registry import ToolDefinition

class XmlExampleProvider:
    """Provides a tool usage example formatted as a single XML string."""

    def __init__(self):
        self._registry = XmlExampleFormatterRegistry()

    def provide(self, tool_definition: 'ToolDefinition', llm_provider: Optional[LLMProvider] = None) -> str:
        """
        Generates a single XML string for a tool usage example.

        Args:
            tool_definition: A ToolDefinition object.
            llm_provider: Ignored, for API consistency.

        Returns:
            A string containing the XML tool usage example.
        """
        formatter = self._registry.get_formatter(llm_provider)
        return formatter.provide(tool_definition)
