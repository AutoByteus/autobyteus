# file: autobyteus/autobyteus/tools/usage/formatters/gemini_json_schema_formatter.py
from typing import Dict, TYPE_CHECKING

from .base_formatter import BaseSchemaFormatter

if TYPE_CHECKING:
    from autobyteus.tools.registry import ToolDefinition

class GeminiJsonSchemaFormatter(BaseSchemaFormatter):
    """Formats a tool's schema into a Google Gemini function declaration format."""

    def provide(self, tool_definition: 'ToolDefinition') -> Dict:
        name = tool_definition.name
        description = tool_definition.description
        arg_schema = tool_definition.argument_schema

        parameters = arg_schema.to_json_schema_dict() if arg_schema else {
            "type": "object", "properties": {}, "required": []
        }

        return {
            "name": name,
            "description": description,
            "parameters": parameters,
        }
