# file: autobyteus/autobyteus/tools/usage/formatters/default_json_example_formatter.py
import json
from typing import Dict, Any, TYPE_CHECKING, List, Optional, Union

from autobyteus.utils.parameter_schema import ParameterType, ParameterDefinition, ParameterSchema
from .base_formatter import BaseExampleFormatter

if TYPE_CHECKING:
    from autobyteus.tools.registry import ToolDefinition

class DefaultJsonExampleFormatter(BaseExampleFormatter):
    """
    Formats a tool usage example into a generic JSON format.
    It intelligently generates detailed examples for complex object schemas, providing
    both a basic (required parameters only) and an advanced (all parameters) example
    if optional parameters are available.
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
        """Helper to create the full tool call example structure for a given mode."""
        tool_name = tool_definition.name
        arg_schema = tool_definition.argument_schema
        arguments = {}

        if arg_schema and arg_schema.parameters:
            params_to_render = arg_schema.parameters
            if mode == 'basic':
                # In basic mode, we only render required parameters.
                params_to_render = [p for p in arg_schema.parameters if p.required]
            
            for param_def in params_to_render:
                arguments[param_def.name] = self._generate_placeholder_value(param_def, mode=mode)

        return {
            "tool": {
                "function": tool_name,
                "parameters": arguments,
            },
        }

    def _schema_has_advanced_params(self, schema: Optional[ParameterSchema]) -> bool:
        """Recursively checks if a schema or any of its sub-schemas have non-required parameters."""
        if not schema:
            return False
        for param in schema.parameters:
            if not param.required:
                return True  # Found an optional param at this level
            if param.object_schema and self._schema_has_advanced_params(param.object_schema):
                return True  # Found an optional param in a nested object
            if isinstance(param.array_item_schema, ParameterSchema) and self._schema_has_advanced_params(param.array_item_schema):
                return True  # Found an optional param in an array of objects
        return False

    def _generate_placeholder_value(self, param_def: ParameterDefinition, mode: str = 'basic') -> Any:
        """
        Generates a placeholder value for a parameter, recursing for complex types.
        The mode determines whether to include optional fields in nested structures.
        """
        # If an object parameter has a detailed schema, generate a structured example from it.
        if param_def.param_type == ParameterType.OBJECT and param_def.object_schema:
            return DefaultJsonExampleFormatter._generate_example_from_schema(param_def.object_schema, param_def.object_schema, mode=mode)
        
        # Handle arrays with a detailed item schema.
        if param_def.param_type == ParameterType.ARRAY and param_def.array_item_schema:
            # Generate one example item for the array to keep it concise.
            example_item = DefaultJsonExampleFormatter._generate_example_from_schema(param_def.array_item_schema, param_def.array_item_schema, mode=mode)
            return [example_item]

        # Fallback to simple placeholder generation for primitives or objects without schemas.
        if param_def.default_value is not None: return param_def.default_value
        if param_def.param_type == ParameterType.STRING: return f"example_{param_def.name}"
        if param_def.param_type == ParameterType.INTEGER: return 123
        if param_def.param_type == ParameterType.FLOAT: return 123.45
        if param_def.param_type == ParameterType.BOOLEAN: return True
        if param_def.param_type == ParameterType.ENUM: return param_def.enum_values[0] if param_def.enum_values else "enum_val"
        if param_def.param_type == ParameterType.OBJECT: return {"key": "value"}
        if param_def.param_type == ParameterType.ARRAY: return ["item1", "item2"] # This now only applies to generic arrays
        return "placeholder"

    @staticmethod
    def _generate_example_from_schema(
        sub_schema: Union[Dict[str, Any], 'ParameterSchema', 'ParameterType'], 
        full_schema: Union[Dict[str, Any], 'ParameterSchema', 'ParameterType'], 
        mode: str = 'basic'
    ) -> Any:
        """
        Recursively generates an example value from a JSON schema dictionary.
        This is a static method so it can be reused by other formatters.
        The 'mode' parameter controls whether optional fields are included in nested objects.
        The default mode is 'basic' to maintain backward compatibility.
        """
        # FIX: Handle primitive ParameterType for array items directly.
        if isinstance(sub_schema, ParameterType):
            if sub_schema == ParameterType.STRING: return "example_string"
            if sub_schema == ParameterType.INTEGER: return 1
            if sub_schema == ParameterType.FLOAT: return 1.1
            if sub_schema == ParameterType.BOOLEAN: return True
            return "unknown_primitive"

        if isinstance(sub_schema, ParameterSchema):
            sub_schema = sub_schema.to_json_schema_dict()
        if isinstance(full_schema, ParameterSchema):
            full_schema = full_schema.to_json_schema_dict()

        if "$ref" in sub_schema:
            ref_path = sub_schema["$ref"]
            try:
                # Resolve the reference, e.g., "#/$defs/MySchema"
                parts = ref_path.lstrip("#/").split("/")
                resolved_schema = full_schema
                for part in parts:
                    resolved_schema = resolved_schema[part]
                return DefaultJsonExampleFormatter._generate_example_from_schema(resolved_schema, full_schema, mode=mode)
            except (KeyError, IndexError):
                return {"error": f"Could not resolve schema reference: {ref_path}"}

        schema_type = sub_schema.get("type")
        
        if "default" in sub_schema:
            return sub_schema["default"]
        
        if "enum" in sub_schema and sub_schema["enum"]:
            return sub_schema["enum"][0]

        if schema_type == "object":
            example_obj = {}
            properties = sub_schema.get("properties", {})
            required_fields = sub_schema.get("required", [])
            for prop_name, prop_schema in properties.items():
                # Include fields if in 'advanced' mode or if they are required.
                if mode == 'advanced' or prop_name in required_fields:
                    example_obj[prop_name] = DefaultJsonExampleFormatter._generate_example_from_schema(prop_schema, full_schema, mode=mode)
            return example_obj
        
        elif schema_type == "array":
            items_schema = sub_schema.get("items")
            if isinstance(items_schema, dict):
                # Generate one example item for the array to keep it concise.
                return [DefaultJsonExampleFormatter._generate_example_from_schema(items_schema, full_schema, mode=mode)]
            else:
                return ["example_item_1"]

        elif schema_type == "string":
            description = sub_schema.get("description", "")
            if "e.g." in description.lower():
                try:
                    return description.split("e.g.,")[1].split(')')[0].strip().strip("'\"")
                except IndexError:
                    pass
            return "example_string"
        
        elif schema_type == "integer":
            return 1
            
        elif schema_type == "number":
            return 1.1
            
        elif schema_type == "boolean":
            return True
        
        elif schema_type == "null":
            return None

        return "unknown_type"
