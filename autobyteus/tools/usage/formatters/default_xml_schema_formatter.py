# file: autobyteus/autobyteus/tools/usage/formatters/default_xml_schema_formatter.py
import xml.sax.saxutils
from typing import TYPE_CHECKING, List, Dict

from autobyteus.utils.parameter_schema import ParameterType, ParameterDefinition, ParameterSchema
from .base_formatter import BaseSchemaFormatter

if TYPE_CHECKING:
    from autobyteus.tools.registry import ToolDefinition

class DefaultXmlSchemaFormatter(BaseSchemaFormatter):
    """Formats a tool's schema into a standardized, potentially nested, XML string."""

    def provide(self, tool_definition: 'ToolDefinition') -> str:
        tool_name = tool_definition.name
        description = tool_definition.description
        arg_schema = tool_definition.argument_schema

        escaped_description = xml.sax.saxutils.escape(description) if description else ""
        tool_tag = f'<tool name="{tool_name}" description="{escaped_description}">'
        xml_parts = [tool_tag]

        if arg_schema and arg_schema.parameters:
            xml_parts.append("    <arguments>")
            xml_parts.extend(self._format_params_recursively(arg_schema.parameters, 2))
            xml_parts.append("    </arguments>")
        else:
            xml_parts.append("    <!-- This tool takes no arguments -->")

        xml_parts.append("</tool>")
        return "\n".join(xml_parts)

    def _json_schema_props_to_param_defs(self, schema_dict: Dict) -> List[ParameterDefinition]:
        """
        Converts a JSON schema's 'properties' dictionary into a list of ParameterDefinition objects.
        This is used to bridge raw JSON schemas with the internal formatting logic.
        """
        param_defs = []
        properties = schema_dict.get("properties", {})
        required_fields = schema_dict.get("required", [])

        for prop_name, prop_schema in properties.items():
            if not isinstance(prop_schema, dict):
                continue

            param_type_str = prop_schema.get("type", "string").upper()
            param_type = getattr(ParameterType, param_type_str, ParameterType.STRING)

            # JSON Schema uses 'enum' key for enumerations
            allowed_values = prop_schema.get("enum")
            if param_type == ParameterType.STRING and allowed_values:
                param_type = ParameterType.ENUM

            object_schema = None
            if param_type == ParameterType.OBJECT and "properties" in prop_schema:
                # Recursively build a ParameterSchema for nested objects
                nested_param_defs = self._json_schema_props_to_param_defs(prop_schema)
                object_schema = ParameterSchema(parameters=nested_param_defs)
            
            array_item_schema = None
            if param_type == ParameterType.ARRAY and "items" in prop_schema:
                # Pass the nested schema down; it will be handled by the next recursive call
                array_item_schema = prop_schema["items"]

            param_defs.append(ParameterDefinition(
                name=prop_name,
                param_type=param_type,
                description=prop_schema.get("description", ""),
                required=(prop_name in required_fields),
                enum_values=allowed_values,
                object_schema=object_schema,
                array_item_schema=array_item_schema
            ))
        return param_defs

    def _format_params_recursively(self, params: List[ParameterDefinition], indent_level: int) -> List[str]:
        """Recursively formats parameter definitions into XML strings."""
        xml_lines = []
        indent = "    " * indent_level

        for param in params:
            attrs = [
                f'name="{param.name}"',
                f'type="{param.param_type.value}"'
            ]
            if param.description:
                attrs.append(f'description="{xml.sax.saxutils.escape(param.description)}"')
            
            attrs.append(f"required=\"{'true' if param.required else 'false'}\"")

            if param.default_value is not None:
                attrs.append(f'default="{xml.sax.saxutils.escape(str(param.default_value))}"')
            if param.param_type == ParameterType.ENUM and param.enum_values:
                escaped_enum = [xml.sax.saxutils.escape(ev) for ev in param.enum_values]
                attrs.append(f'enum_values="{",".join(escaped_enum)}"')

            is_object = param.param_type == ParameterType.OBJECT and param.object_schema
            is_array = param.param_type == ParameterType.ARRAY and param.array_item_schema

            if is_object:
                xml_lines.append(f'{indent}<arg {" ".join(attrs)}>')
                xml_lines.extend(self._format_params_recursively(param.object_schema.parameters, indent_level + 1))
                xml_lines.append(f'{indent}</arg>')
            elif is_array:
                xml_lines.append(f'{indent}<arg {" ".join(attrs)}>')
                if isinstance(param.array_item_schema, ParameterSchema):
                    # Array of objects defined with our internal ParameterSchema
                    xml_lines.append(f'{indent}    <items type="object">')
                    xml_lines.extend(self._format_params_recursively(param.array_item_schema.parameters, indent_level + 2))
                    xml_lines.append(f'{indent}    </items>')
                elif isinstance(param.array_item_schema, ParameterType):
                    # Array of primitives
                    xml_lines.append(f'{indent}    <items type="{param.array_item_schema.value}" />')
                elif isinstance(param.array_item_schema, dict):
                    # FIX: Handle array of objects defined with a raw JSON schema dict
                    item_schema_dict = param.array_item_schema
                    item_type = item_schema_dict.get("type", "string")
                    
                    xml_lines.append(f'{indent}    <items type="{item_type}">')
                    
                    if item_type == "object":
                        # Convert the JSON schema properties to our internal ParameterDefinition list
                        param_defs = self._json_schema_props_to_param_defs(item_schema_dict)
                        xml_lines.extend(self._format_params_recursively(param_defs, indent_level + 2))

                    xml_lines.append(f'{indent}    </items>')
                xml_lines.append(f'{indent}</arg>')
            else:
                # This is a simple/primitive type or a generic array
                xml_lines.append(f'{indent}<arg {" ".join(attrs)} />')

        return xml_lines
