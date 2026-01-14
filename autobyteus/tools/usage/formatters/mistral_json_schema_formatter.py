from typing import Dict, TYPE_CHECKING
from .base_formatter import BaseSchemaFormatter

if TYPE_CHECKING:
    from autobyteus.tools.registry import ToolDefinition

class MistralJsonSchemaFormatter(BaseSchemaFormatter):
    """Formats a tool's schema into the Mistral JSON format (standard JSON schema)."""

    def provide(self, tool_definition: 'ToolDefinition') -> Dict:
        return {
            "type": "function",
            "function": {
                "name": tool_definition.name,
                "description": tool_definition.description,
                "parameters": tool_definition.argument_schema.to_json_schema_dict() if tool_definition.argument_schema else {"type": "object", "properties": {}}
            }
        }
