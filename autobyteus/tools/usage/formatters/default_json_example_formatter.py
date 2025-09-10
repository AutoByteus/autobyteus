# file: autobyteus/autobyteus/tools/usage/formatters/default_json_example_formatter.py
from typing import Dict, Any, TYPE_CHECKING, List, Optional, Union

from autobyteus.tools.parameter_schema import ParameterType, ParameterDefinition, ParameterSchema
from .base_formatter import BaseExampleFormatter

if TYPE_CHECKING:
    from autobyteus.tools.registry import ToolDefinition

class DefaultJsonExampleFormatter(BaseExampleFormatter):
    """
    Formats a tool usage example into a generic JSON format.
    It intelligently generates detailed examples for complex object schemas.
    """

    def provide(self, tool_definition: 'ToolDefinition') -> Dict:
        tool_name = tool_definition.name
        arg_schema = tool_definition.argument_schema
        arguments = {}

        if arg_schema and arg_schema.parameters:
            for param_def in arg_schema.parameters:
                # Always include required parameters in the example.
                # Also include optional parameters that have a default value to show common usage.
                if param_def.required or param_def.default_value is not None:
                    arguments[param_def.name] = self._generate_placeholder_value(param_def)

        return {
            "tool": {
                "function": tool_name,
                "parameters": arguments,
            },
        }

    def _generate_placeholder_value(self, param_def: ParameterDefinition) -> Any:
        # If an object parameter has a detailed schema, generate a structured example from it.
        if param_def.param_type == ParameterType.OBJECT and param_def.object_schema:
            return DefaultJsonExampleFormatter._generate_example_from_schema(param_def.object_schema, param_def.object_schema)
        
        # --- FIX: Handle arrays with a detailed item schema ---
        if param_def.param_type == ParameterType.ARRAY and param_def.array_item_schema:
            # Generate one example item for the array to keep it concise.
            # We pass the item schema as both sub_schema and full_schema for potential self-references within.
            example_item = DefaultJsonExampleFormatter._generate_example_from_schema(param_def.array_item_schema, param_def.array_item_schema)
            return [example_item]
        # --- END FIX ---

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
    def _generate_example_from_schema(sub_schema: Union[Dict[str, Any], 'ParameterSchema'], full_schema: Union[Dict[str, Any], 'ParameterSchema']) -> Any:
        """
        Recursively generates an example value from a JSON schema dictionary.
        This is a static method so it can be reused by other formatters.
        """
        # --- FIX: Handle ParameterSchema objects by converting them to dicts ---
        if isinstance(sub_schema, ParameterSchema):
            sub_schema = sub_schema.to_json_schema_dict()
        if isinstance(full_schema, ParameterSchema):
            full_schema = full_schema.to_json_schema_dict()
        # --- END FIX ---

        if "$ref" in sub_schema:
            ref_path = sub_schema["$ref"]
            try:
                # Resolve the reference, e.g., "#/$defs/MySchema"
                parts = ref_path.lstrip("#/").split("/")
                resolved_schema = full_schema
                for part in parts:
                    resolved_schema = resolved_schema[part]
                return DefaultJsonExampleFormatter._generate_example_from_schema(resolved_schema, full_schema)
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
                # Include required fields and a subset of optional fields for a concise example.
                if prop_name in required_fields:
                    example_obj[prop_name] = DefaultJsonExampleFormatter._generate_example_from_schema(prop_schema, full_schema)
            return example_obj
        
        elif schema_type == "array":
            items_schema = sub_schema.get("items")
            if isinstance(items_schema, dict):
                # Generate one example item for the array to keep it concise
                return [DefaultJsonExampleFormatter._generate_example_from_schema(items_schema, full_schema)]
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
