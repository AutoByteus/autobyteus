# file: autobyteus/autobyteus/tools/usage/providers/json_schema_provider.py
from typing import Optional, Dict, TYPE_CHECKING

from autobyteus.llm.providers import LLMProvider
from autobyteus.tools.usage.registries.json_schema_formatter_registry import JsonSchemaFormatterRegistry

if TYPE_CHECKING:
    from autobyteus.tools.registry import ToolDefinition

class JsonSchemaProvider:
    """
    Provides the schema for a single tool formatted as a JSON dictionary,
    tailored to the specific LLM provider's requirements.
    """
    def __init__(self):
        self._registry = JsonSchemaFormatterRegistry()

    def provide(self, tool_definition: 'ToolDefinition', llm_provider: Optional[LLMProvider] = None) -> Dict:
        """
        Generates a JSON dictionary for a single tool's schema.

        Args:
            tool_definition: A ToolDefinition object.
            llm_provider: The LLMProvider for which to format the JSON. If None,
                          a default generic format is used.

        Returns:
            A dictionary representing the tool schema.
        """
        if llm_provider:
            formatter = self._registry.get_formatter(llm_provider)
        else:
            formatter = self._registry.get_default_formatter()

        return formatter.provide(tool_definition)
