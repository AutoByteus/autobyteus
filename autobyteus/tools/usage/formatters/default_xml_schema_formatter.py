# file: autobyteus/autobyteus/tools/usage/formatters/default_xml_schema_formatter.py
import xml.sax.saxutils
from typing import TYPE_CHECKING, List

from autobyteus.tools.parameter_schema import ParameterType, ParameterDefinition, ParameterSchema
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
                    # Array of objects
                    xml_lines.append(f'{indent}    <items type="object">')
                    xml_lines.extend(self._format_params_recursively(param.array_item_schema.parameters, indent_level + 2))
                    xml_lines.append(f'{indent}    </items>')
                elif isinstance(param.array_item_schema, ParameterType):
                    # Array of primitives
                    xml_lines.append(f'{indent}    <items type="{param.array_item_schema.value}" />')
                xml_lines.append(f'{indent}</arg>')
            else:
                # This is a simple/primitive type or a generic array
                xml_lines.append(f'{indent}<arg {" ".join(attrs)} />')

        return xml_lines
