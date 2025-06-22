# file: autobyteus/autobyteus/tools/usage/formatters/openai_json_example_formatter.py
import json
from typing import Dict, Any, TYPE_CHECKING

from autobyteus.tools.parameter_schema import ParameterType, ParameterDefinition
from .base_formatter import BaseExampleFormatter

if TYPE_CHECKING:
    from autobyteus.tools.registry import ToolDefinition

class OpenAiJsonExampleFormatter(BaseExampleFormatter):
    """
    Formats a tool usage example into a format resembling an entry in the
    OpenAI JSON 'tool_calls' array, intended for prompting a model.
    The output is wrapped in a 'tool' key for consistency in prompts.
    """

    def provide(self, tool_definition: 'ToolDefinition') -> Dict:
        tool_name = tool_definition.name
        arg_schema = tool_definition.argument_schema
        arguments = {}

        if arg_schema and arg_schema.parameters:
            for param_def in arg_schema.parameters:
                if param_def.required or param_def.default_value is not None:
                    arguments[param_def.name] = self._generate_placeholder_value(param_def)

        # This format contains the 'function' wrapper with a stringified 'arguments' field.
        # This aligns with the structure often seen inside an OpenAI API tool_calls object.
        function_call = {
            "function": {
                "name": tool_name,
                "arguments": json.dumps(arguments),
            },
        }

        # Wrap in a 'tool' key for consistency in prompt generation.
        return {"tool": function_call}

    def _generate_placeholder_value(self, param_def: ParameterDefinition) -> Any:
        if param_def.default_value is not None: return param_def.default_value
        if param_def.param_type == ParameterType.STRING: return f"example_{param_def.name}"
        if param_def.param_type == ParameterType.INTEGER: return 123
        if param_def.param_type == ParameterType.FLOAT: return 123.45
        if param_def.param_type == ParameterType.BOOLEAN: return True
        if param_def.param_type == ParameterType.ENUM: return param_def.enum_values[0] if param_def.enum_values else "enum_val"
        if param_def.param_type == ParameterType.OBJECT: return {"key": "value"}
        if param_def.param_type == ParameterType.ARRAY: return ["item1", "item2"]
        return "placeholder"
