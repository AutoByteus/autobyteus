# file: autobyteus/autobyteus/tools/usage/providers/tool_manifest_provider.py
import logging
import json
from typing import TYPE_CHECKING, List, Optional

if TYPE_CHECKING:
    from autobyteus.tools.registry import ToolDefinition

logger = logging.getLogger(__name__)

class ToolManifestProvider:
    """
    Generates a complete tool manifest string, which includes the schema
    and an example for each provided tool. This is suitable for injection
    into a system prompt.
    """
    SCHEMA_HEADER = "## Tool Definition:"
    EXAMPLE_HEADER = "## Example Usage:"
    JSON_EXAMPLE_HEADER = "To use this tool, you MUST output a JSON object in the following format:"

    def provide(self,
                tool_definitions: List['ToolDefinition'],
                use_xml: bool,
                provider: Optional[str] = None) -> str:
        """
        Generates the manifest string for a list of tools.

        Args:
            tool_definitions: A list of ToolDefinition objects.
            use_xml: If True, generate in XML format. Otherwise, use JSON.
            provider: The LLM provider name, for provider-specific formatting.

        Returns:
            A single string containing the formatted manifest.
        """
        tool_blocks = []

        for td in tool_definitions:
            try:
                if use_xml:
                    schema = td.get_usage_xml(provider=provider)
                    example = td.get_usage_xml_example(provider=provider)
                    if schema and example:
                        tool_blocks.append(f"{self.SCHEMA_HEADER}\n{schema}\n\n{self.EXAMPLE_HEADER}\n{example}")
                    else:
                        logger.warning(f"Could not generate schema or example for XML tool '{td.name}'.")
                else:  # JSON format
                    schema = td.get_usage_json(provider=provider)
                    example = td.get_usage_json_example(provider=provider)
                    if schema and example:
                        # Per user feedback, wrap schema in a 'tool' key.
                        schema_wrapped = {"tool": schema}
                        schema_str = json.dumps(schema_wrapped, indent=2)
                        
                        # Example is already formatted correctly by the example formatter.
                        example_str = json.dumps(example, indent=2)

                        tool_blocks.append(f"{self.SCHEMA_HEADER}\n{schema_str}\n\n{self.JSON_EXAMPLE_HEADER}\n{example_str}")
                    else:
                        logger.warning(f"Could not generate schema or example for JSON tool '{td.name}'.")

            except Exception as e:
                logger.error(f"Failed to generate manifest block for tool '{td.name}': {e}", exc_info=True)

        if use_xml:
            return "\n\n---\n\n".join(tool_blocks)
        else: 
            return "[\n" + ",\n".join(tool_blocks) + "\n]"
