# file: autobyteus/autobyteus/tools/usage/providers/xml_schema_provider.py
from typing import Optional, TYPE_CHECKING

from autobyteus.llm.providers import LLMProvider
from autobyteus.tools.usage.registries.xml_schema_formatter_registry import XmlSchemaFormatterRegistry

if TYPE_CHECKING:
    from autobyteus.tools.registry import ToolDefinition

class XmlSchemaProvider:
    """
    Provides the schema for a single tool formatted as an XML string.
    """
    def __init__(self):
        self._registry = XmlSchemaFormatterRegistry()

    def provide(self, tool_definition: 'ToolDefinition', llm_provider: Optional[LLMProvider] = None) -> str:
        """
        Generates an XML string for a single tool's schema.

        Args:
            tool_definition: A ToolDefinition object.
            llm_provider: This argument is passed to the registry for API consistency.

        Returns:
            A string containing the XML tool schema.
        """
        formatter = self._registry.get_formatter(llm_provider)
        return formatter.provide(tool_definition)
