# file: autobyteus/autobyteus/tools/usage/providers/json_example_provider.py
from typing import Optional, Any, TYPE_CHECKING

from autobyteus.llm.providers import LLMProvider
from autobyteus.tools.usage.registries.json_example_formatter_registry import JsonExampleFormatterRegistry

if TYPE_CHECKING:
    from autobyteus.tools.registry import ToolDefinition

class JsonExampleProvider:
    """Provides a tool usage example as a JSON dictionary for a specific LLM provider."""

    def __init__(self):
        self._registry = JsonExampleFormatterRegistry()

    def provide(self, tool_definition: 'ToolDefinition', llm_provider: Optional[LLMProvider] = None) -> Any:
        """
        Generates a JSON dictionary or string for a single tool usage example.

        Args:
            tool_definition: A ToolDefinition object.
            llm_provider: The LLMProvider for which to format the JSON.

        Returns:
            A dictionary or string representing the tool usage example.
        """
        if llm_provider:
            formatter = self._registry.get_formatter(llm_provider)
        else:
            formatter = self._registry.get_default_formatter()

        return formatter.provide(tool_definition)
