# file: autobyteus/autobyteus/tools/usage/formatters/default_xml_example_formatter.py
import xml.sax.saxutils
import json # Import json for embedding complex objects
from typing import Any, TYPE_CHECKING

from autobyteus.tools.parameter_schema import ParameterType, ParameterDefinition
from .base_formatter import BaseExampleFormatter
from .default_json_example_formatter import DefaultJsonExampleFormatter # Import for reuse

if TYPE_CHECKING:
    from autobyteus.tools.registry import ToolDefinition

class DefaultXmlExampleFormatter(BaseExampleFormatter):
    """Formats a tool usage example into a standardized XML <tool> string."""

    def provide(self, tool_definition: 'ToolDefinition') -> str:
        tool_name = tool_definition.name
        arg_schema = tool_definition.argument_schema

        example_xml_parts = [f'<tool name="{tool_name}">']
        arguments_part = []

        if arg_schema and arg_schema.parameters:
            for param_def in arg_schema.parameters:
                if param_def.required or param_def.default_value is not None:
                    placeholder_value = self._generate_placeholder_value(param_def)
                    # For complex objects/arrays, we now get a dict/list.
                    # Convert it to a JSON string for embedding in XML.
                    if isinstance(placeholder_value, (dict, list)):
                        value_str = json.dumps(placeholder_value, indent=2)
                    else:
                        value_str = str(placeholder_value)

                    escaped_value = xml.sax.saxutils.escape(value_str)
                    
                    # Add newlines for readability if the value is a multiline JSON string
                    if '\n' in escaped_value:
                        arguments_part.append(f'        <arg name="{param_def.name}">\n{escaped_value}\n        </arg>')
                    else:
                        arguments_part.append(f'        <arg name="{param_def.name}">{escaped_value}</arg>')


        if arguments_part:
            example_xml_parts.append("    <arguments>")
            example_xml_parts.extend(arguments_part)
            example_xml_parts.append("    </arguments>")
        else:
            example_xml_parts.append("    <!-- This tool takes no arguments -->")

        example_xml_parts.append("</tool>")
        return "\n".join(example_xml_parts)

    def _generate_placeholder_value(self, param_def: ParameterDefinition) -> Any:
        # REUSE a more intelligent generator for complex objects
        if param_def.param_type == ParameterType.OBJECT and param_def.object_schema:
            return DefaultJsonExampleFormatter._generate_example_from_schema(param_def.object_schema, param_def.object_schema)

        # Fallback for primitives
        if param_def.default_value is not None:
            return param_def.default_value
        if param_def.param_type == ParameterType.STRING:
            return f"example_{param_def.name}"
        if param_def.param_type == ParameterType.INTEGER:
            return 123
        if param_def.param_type == ParameterType.FLOAT:
            return 123.45
        if param_def.param_type == ParameterType.BOOLEAN:
            return True
        if param_def.param_type == ParameterType.ENUM:
            return param_def.enum_values[0] if param_def.enum_values else "enum_val"
        if param_def.param_type == ParameterType.OBJECT:
            return {"key": "value"} # Fallback if no schema
        if param_def.param_type == ParameterType.ARRAY:
            return ["item1", "item2"]
        return "placeholder"
