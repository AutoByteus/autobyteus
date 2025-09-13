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
    # --- XML Specific Headers and Guidelines ---
    XML_SCHEMA_HEADER = "## Tool Definition:"
    XML_EXAMPLE_HEADER = "## Tool Usage Examples and Guidelines:"
    XML_GENERAL_GUIDELINES = (
        "To use this tool, you must construct an XML block exactly like the examples below. "
        "Ensure all tags are correctly named and nested. Pay close attention to how arguments, "
        "especially complex ones like lists and objects, are formatted."
    )
    XML_ARRAY_GUIDELINES = (
        "Formatting Lists/Arrays: For any argument that is a list (an array), you MUST wrap each "
        "individual value in its own `<item>` tag. Do not use comma-separated strings or JSON-style `[...]` arrays within a single tag.\n\n"
        "Correct:\n"
        '<arg name="dependencies">\n'
        '    <item>task_1</item>\n'
        '    <item>task_2</item>\n'
        '</arg>\n\n'
        "Incorrect:\n"
        '<arg name="dependencies">[task_1, task_2]</arg>\n'
        '<arg name="dependencies">task_1, task_2</arg>'
    )
    
    # --- JSON Specific Headers ---
    JSON_SCHEMA_HEADER = "## Tool Definition:"
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

        formatter_pair = self._formatting_registry.get_formatter_pair(provider, use_xml_tool_format=use_xml_tool_format)
        schema_formatter = formatter_pair.schema_formatter
        example_formatter = formatter_pair.example_formatter

        is_xml_format = isinstance(schema_formatter, DefaultXmlSchemaFormatter)

        for td in tool_definitions:
            try:
                schema = schema_formatter.provide(td)
                example = example_formatter.provide(td) # This is now a pre-formatted string for both XML and JSON

                if schema and example:
                    if is_xml_format:
                        tool_blocks.append(f"{self.XML_SCHEMA_HEADER}\n{schema}\n\n{self.XML_EXAMPLE_HEADER}\n{example}")
                    else:
                        # For JSON, the schema is a dict, but the example is now a pre-formatted string.
                        schema_str = json.dumps(schema, indent=2)
                        # FIX: Do NOT call json.dumps() on the 'example' variable, as it is already a string.
                        tool_blocks.append(f"{self.JSON_SCHEMA_HEADER}\n{schema_str}\n\n{self.JSON_EXAMPLE_HEADER}\n{example}")
                else:
                    logger.warning(f"Could not generate schema or example for tool '{td.name}' using format {'XML' if is_xml_format else 'JSON'}.")

            except Exception as e:
                logger.error(f"Failed to generate manifest block for tool '{td.name}': {e}", exc_info=True)
        
        # Assemble the final manifest string
        manifest_content = "\n\n---\n\n".join(tool_blocks)

        if is_xml_format and manifest_content:
            # Prepend the general guidelines for XML format
            return f"{self.XML_GENERAL_GUIDELINES}\n\n{self.XML_ARRAY_GUIDELINES}\n\n---\n\n{manifest_content}"
        
        return manifest_content
