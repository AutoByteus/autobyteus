# file: autobyteus/autobyteus/tools/usage/formatters/gemini_json_example_formatter.py
from typing import Dict, Any, TYPE_CHECKING

from autobyteus.tools.parameter_schema import ParameterType, ParameterDefinition
from .base_formatter import BaseExampleFormatter
from .default_json_example_formatter import DefaultJsonExampleFormatter # Import for reuse

if TYPE_CHECKING:
    from autobyteus.tools.registry import ToolDefinition

class GeminiJsonExampleFormatter(BaseExampleFormatter):
    """Formats a tool usage example into the Google Gemini tool_calls format."""

    def provide(self, tool_definition: 'ToolDefinition') -> Dict:
        tool_name = tool_definition.name
        arg_schema = tool_definition.argument_schema
        arguments = {}

        if arg_schema and arg_schema.parameters:
            for param_def in arg_schema.parameters:
                if param_def.required or param_def.default_value is not None:
                    arguments[param_def.name] = self._generate_placeholder_value(param_def)

        return {"name": tool_name, "args": arguments}

    def _generate_placeholder_value(self, param_def: ParameterDefinition) -> Any:
        # REUSE a more intelligent generator for complex objects
        if param_def.param_type == ParameterType.OBJECT and param_def.object_schema:
            return DefaultJsonExampleFormatter._generate_example_from_schema(param_def.object_schema, param_def.object_schema)
            
        # Fallback for primitives
        if param_def.default_value is not None: return param_def.default_value
        if param_def.param_type == ParameterType.STRING: return f"example_{param_def.name}"
        if param_def.param_type == ParameterType.INTEGER: return 123
        if param_def.param_type == ParameterType.FLOAT: return 123.45
        if param_def.param_type == ParameterType.BOOLEAN: return True
        if param_def.param_type == ParameterType.ENUM: return param_def.enum_values[0] if param_def.enum_values else "enum_val"
        if param_def.param_type == ParameterType.OBJECT: return {"key": "value"}
        if param_def.param_type == ParameterType.ARRAY: return ["item1", "item2"]
        return "placeholder"
