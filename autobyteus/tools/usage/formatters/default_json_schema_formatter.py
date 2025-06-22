# file: autobyteus/autobyteus/tools/usage/formatters/default_json_schema_formatter.py
from typing import Dict, TYPE_CHECKING

from .base_formatter import BaseSchemaFormatter

if TYPE_CHECKING:
    from autobyteus.tools.registry import ToolDefinition

class DefaultJsonSchemaFormatter(BaseSchemaFormatter):
    """
    Formats a tool's schema into a generic, provider-agnostic JSON format.
    This serves as the default for JSON-based schema representation.
    """

    def provide(self, tool_definition: 'ToolDefinition') -> Dict:
        name = tool_definition.name
        description = tool_definition.description
        arg_schema = tool_definition.argument_schema

        input_schema = arg_schema.to_json_schema_dict() if arg_schema else {
            "type": "object", "properties": {}, "required": []
        }

        return {
            "name": name,
            "description": description,
            "inputSchema": input_schema,
        }
