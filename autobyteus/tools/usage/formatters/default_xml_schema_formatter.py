# file: autobyteus/autobyteus/tools/usage/formatters/default_xml_schema_formatter.py
import xml.sax.saxutils
from typing import TYPE_CHECKING

from autobyteus.tools.parameter_schema import ParameterType
from .base_formatter import BaseSchemaFormatter

if TYPE_CHECKING:
    from autobyteus.tools.registry import ToolDefinition

class DefaultXmlSchemaFormatter(BaseSchemaFormatter):
    """Formats a tool's schema into a standardized XML string."""

    def provide(self, tool_definition: 'ToolDefinition') -> str:
        arg_schema = tool_definition.argument_schema
        tool_name = tool_definition.name
        description = tool_definition.description

        escaped_description = xml.sax.saxutils.escape(description) if description else ""
        tool_tag = f'<tool name="{tool_name}" description="{escaped_description}">'
        xml_parts = [tool_tag]

        if arg_schema and arg_schema.parameters:
            xml_parts.append("    <arguments>")
            for param in arg_schema.parameters:
                arg_tag = f'        <arg name="{param.name}"'
                arg_tag += f' type="{param.param_type.value}"'
                if param.description:
                    escaped_param_desc = xml.sax.saxutils.escape(param.description)
                    arg_tag += f' description="{escaped_param_desc}"'
                arg_tag += f" required=\"{'true' if param.required else 'false'}\""

                if param.default_value is not None:
                    arg_tag += f' default="{xml.sax.saxutils.escape(str(param.default_value))}"'
                if param.param_type == ParameterType.ENUM and param.enum_values:
                    escaped_enum_values = [xml.sax.saxutils.escape(ev) for ev in param.enum_values]
                    arg_tag += f' enum_values="{",".join(escaped_enum_values)}"'

                arg_tag += " />"
                xml_parts.append(arg_tag)
            xml_parts.append("    </arguments>")
        else:
            xml_parts.append("    <!-- This tool takes no arguments -->")

        xml_parts.append("</tool>")
        return "\n".join(xml_parts)
