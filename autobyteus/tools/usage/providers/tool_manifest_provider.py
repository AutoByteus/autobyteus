# file: autobyteus/autobyteus/tools/usage/providers/tool_manifest_provider.py
import logging
import json
from typing import TYPE_CHECKING, List, Optional

from autobyteus.llm.providers import LLMProvider
from autobyteus.tools.usage.registries.tool_formatting_registry import ToolFormattingRegistry
from autobyteus.tools.usage.formatters import DefaultXmlSchemaFormatter

if TYPE_CHECKING:
    from autobyteus.tools.registry import ToolDefinition

logger = logging.getLogger(__name__)

class ToolManifestProvider:
    """
    Generates a complete tool manifest string, which includes the schema
    and an example for each provided tool. This is suitable for injection
    into a system prompt. It uses the central ToolFormattingRegistry to get
    the correct formatters for the specified provider.
    """
    SCHEMA_HEADER = "## Tool Definition:"
    EXAMPLE_HEADER = "## Example Usage:"
    # UPDATED: Changed the header to be more descriptive as requested.
    JSON_EXAMPLE_HEADER = "Example: To use this tool, you could provide the following JSON object as a tool call:"

    def __init__(self):
        self._formatting_registry = ToolFormattingRegistry()
        logger.debug("ToolManifestProvider initialized.")

    def provide(self,
                tool_definitions: List['ToolDefinition'],
                provider: Optional[LLMProvider] = None,
                use_xml_tool_format: bool = False) -> str:
        """
        Generates the manifest string for a list of tools.

        Args:
            tool_definitions: A list of ToolDefinition objects.
            provider: The LLM provider, for provider-specific formatting.
            use_xml_tool_format: If True, forces the use of XML formatters.

        Returns:
            A single string containing the formatted manifest.
        """
        tool_blocks = []

        # Get the correct formatting pair from the registry, passing the override flag.
        formatter_pair = self._formatting_registry.get_formatter_pair(provider, use_xml_tool_format=use_xml_tool_format)
        schema_formatter = formatter_pair.schema_formatter
        example_formatter = formatter_pair.example_formatter

        # Determine if the chosen formatter is XML-based. This determines the final assembly format.
        is_xml_format = isinstance(schema_formatter, DefaultXmlSchemaFormatter)

        for td in tool_definitions:
            try:
                schema = schema_formatter.provide(td)
                example = example_formatter.provide(td)

                if schema and example:
                    if is_xml_format:
                        tool_blocks.append(f"{self.SCHEMA_HEADER}\n{schema}\n\n{self.EXAMPLE_HEADER}\n{example}")
                    else:  # JSON format
                        # UPDATED: Removed the redundant {"tool": schema} wrapper.
                        schema_str = json.dumps(schema, indent=2)
                        example_str = json.dumps(example, indent=2)
                        tool_blocks.append(f"{self.SCHEMA_HEADER}\n{schema_str}\n\n{self.JSON_EXAMPLE_HEADER}\n{example_str}")
                else:
                    logger.warning(f"Could not generate schema or example for tool '{td.name}' using format {'XML' if is_xml_format else 'JSON'}.")

            except Exception as e:
                logger.error(f"Failed to generate manifest block for tool '{td.name}': {e}", exc_info=True)
        
        # UPDATED: Unify the return for all formats to provide a consistent structure
        # without the incorrect '[]' wrapper for JSON.
        return "\n\n---\n\n".join(tool_blocks)
