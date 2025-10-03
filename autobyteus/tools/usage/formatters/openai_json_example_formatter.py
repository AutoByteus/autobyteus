# file: autobyteus/autobyteus/tools/usage/formatters/openai_json_example_formatter.py
import json
from typing import Dict, Any, TYPE_CHECKING, Optional

from autobyteus.utils.parameter_schema import ParameterSchema, ParameterDefinition
from .base_formatter import BaseExampleFormatter
from .default_json_example_formatter import DefaultJsonExampleFormatter # Import for reuse

if TYPE_CHECKING:
    from autobyteus.tools.registry import ToolDefinition

class OpenAiJsonExampleFormatter(BaseExampleFormatter):
    """
    Formats a tool usage example into the OpenAI JSON 'tool_calls' format.
    Provides both basic (required only) and advanced (all) examples if optional
    parameters exist for the tool.
    """
    
    def provide(self, tool_definition: 'ToolDefinition') -> str:
        """
        Generates a formatted string containing basic and optionally an advanced usage example for the tool.
        """
        basic_example_dict = self._create_example_structure(tool_definition, mode='basic')
        basic_example_str = "### Example 1: Basic Call (Required Arguments)\n"
        basic_example_str += "```json\n"
        basic_example_str += json.dumps(basic_example_dict, indent=2)
        basic_example_str += "\n```"
        
        if not self._schema_has_advanced_params(tool_definition.argument_schema):
            return basic_example_str

        advanced_example_dict = self._create_example_structure(tool_definition, mode='advanced')
        advanced_example_str = "### Example 2: Advanced Call (With Optional Arguments)\n"
        advanced_example_str += "```json\n"
        advanced_example_str += json.dumps(advanced_example_dict, indent=2)
        advanced_example_str += "\n```"
        
        return f"{basic_example_str}\n\n{advanced_example_str}"

    def _create_example_structure(self, tool_definition: 'ToolDefinition', mode: str) -> Dict:
        """Helper to create a single OpenAI tool call example for a given mode."""
        tool_name = tool_definition.name
        arg_schema = tool_definition.argument_schema
        arguments = {}

        if arg_schema and arg_schema.parameters:
            params_to_render = arg_schema.parameters
            if mode == 'basic':
                params_to_render = [p for p in arg_schema.parameters if p.required]
            
            for param_def in params_to_render:
                # Use the intelligent placeholder generator from the default formatter
                arguments[param_def.name] = DefaultJsonExampleFormatter._generate_example_from_schema(
                    param_def.object_schema or param_def.array_item_schema or param_def.param_type, 
                    param_def.object_schema or arg_schema,
                    mode=mode
                ) if param_def.object_schema or param_def.array_item_schema else self._generate_simple_placeholder(param_def)

        function_call = {
            "function": {
                "name": tool_name,
                # FIX: Keep arguments as a dictionary for clear examples in the prompt.
                # Do NOT stringify it here.
                "arguments": arguments,
            },
        }
        return {"tool": function_call}

    def _schema_has_advanced_params(self, schema: Optional[ParameterSchema]) -> bool:
        """Recursively checks if a schema or any of its sub-schemas have non-required parameters."""
        if not schema: return False
        for param in schema.parameters:
            if not param.required: return True
            if param.object_schema and self._schema_has_advanced_params(param.object_schema): return True
            if isinstance(param.array_item_schema, ParameterSchema) and self._schema_has_advanced_params(param.array_item_schema): return True
        return False

    def _generate_simple_placeholder(self, param_def: ParameterDefinition) -> Any:
        """Generates a simple placeholder for primitive types."""
        if param_def.default_value is not None: return param_def.default_value
        return DefaultJsonExampleFormatter._generate_example_from_schema(param_def.param_type, param_def.param_type, mode='basic')
