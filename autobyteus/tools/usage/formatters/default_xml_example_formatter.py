# file: autobyteus/autobyteus/tools/usage/formatters/default_xml_example_formatter.py
import xml.sax.saxutils
import re
from typing import Any, TYPE_CHECKING, List, Optional

from autobyteus.utils.parameter_schema import ParameterType, ParameterDefinition, ParameterSchema
from .base_formatter import BaseExampleFormatter

if TYPE_CHECKING:
    from autobyteus.tools.registry import ToolDefinition

class DefaultXmlExampleFormatter(BaseExampleFormatter):
    """Formats a tool usage example into a standardized, nested XML <tool> string."""

    def provide(self, tool_definition: 'ToolDefinition') -> str:
        """
        Generates a multi-shot example string for the given tool, including
        a basic and an advanced usage case.
        """
        basic_example = self._generate_basic_example(tool_definition)
        advanced_example = self._generate_advanced_example(tool_definition)

        examples = [basic_example]
        if advanced_example:
            examples.append(advanced_example)
        
        return "\n\n".join(examples)

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

    def _generate_basic_example(self, tool_def: 'ToolDefinition') -> str:
        """Generates an XML example including only the required parameters."""
        tool_name = tool_def.name
        arg_schema = tool_def.argument_schema
        
        example_xml_parts = [
            "### Example 1: Basic Call (Required Arguments)",
            f'<tool name="{tool_name}">'
        ]
        
        if arg_schema and any(p.required for p in arg_schema.parameters):
            example_xml_parts.append("    <arguments>")
            arguments_part = self._generate_arguments_xml(arg_schema.parameters, 2, mode='basic')
            example_xml_parts.extend(arguments_part)
            example_xml_parts.append("    </arguments>")
        else:
            example_xml_parts.append("    <!-- This tool has no required arguments. -->")

        example_xml_parts.append("</tool>")
        return "\n".join(example_xml_parts)

    def _generate_advanced_example(self, tool_def: 'ToolDefinition') -> Optional[str]:
        """
        Generates a more complex example if the schema has any optional parameters
        at any level of nesting.
        """
        arg_schema = tool_def.argument_schema
        if not self._schema_has_advanced_params(arg_schema):
            return None
        
        tool_name = tool_def.name
        example_xml_parts = [
            "### Example 2: Advanced Call (With Optional & Nested Arguments)",
            f'<tool name="{tool_name}">'
        ]
        
        if arg_schema and arg_schema.parameters:
             example_xml_parts.append("    <arguments>")
             arguments_part = self._generate_arguments_xml(arg_schema.parameters, 2, mode='advanced')
             example_xml_parts.extend(arguments_part)
             example_xml_parts.append("    </arguments>")
        else:
             return None

        example_xml_parts.append("</tool>")
        return "\n".join(example_xml_parts)

    def _generate_placeholder_value(self, param_def: ParameterDefinition) -> Any:
        """Generates a descriptive placeholder value."""
        if param_def.default_value is not None:
            return param_def.default_value

        if param_def.description:
            match = re.search(r"e\.g\.,?\s*[`']([^`']+)[`']", param_def.description)
            if match:
                return match.group(1)

        if param_def.param_type == ParameterType.STRING:
            return f"A valid string for '{param_def.name}'"
        if param_def.param_type == ParameterType.INTEGER:
            return 123
        if param_def.param_type == ParameterType.FLOAT:
            return 123.45
        if param_def.param_type == ParameterType.BOOLEAN:
            return True
        if param_def.param_type == ParameterType.ENUM:
            return param_def.enum_values[0] if param_def.enum_values else "enum_val"
        return "placeholder"

    def _generate_arguments_xml(self, params: List[ParameterDefinition], indent_level: int, mode: str) -> List[str]:
        """Recursively generates XML for a list of parameter definitions based on the mode."""
        xml_lines = []
        indent = "    " * indent_level

        params_to_render = params
        if mode == 'basic':
            params_to_render = [p for p in params if p.required]

        for param_def in params_to_render:
            param_name = param_def.name
            
            if param_def.param_type == ParameterType.OBJECT and param_def.object_schema:
                xml_lines.append(f'{indent}<arg name="{param_name}">')
                xml_lines.extend(self._generate_arguments_xml(param_def.object_schema.parameters, indent_level + 1, mode=mode))
                xml_lines.append(f'{indent}</arg>')

            elif param_def.param_type == ParameterType.ARRAY:
                xml_lines.append(f'{indent}<arg name="{param_name}">')
                
                if isinstance(param_def.array_item_schema, ParameterSchema): # Array of objects
                    xml_lines.append(f'{indent}    <item>')
                    xml_lines.extend(self._generate_arguments_xml(param_def.array_item_schema.parameters, indent_level + 2, mode=mode))
                    xml_lines.append(f'{indent}    </item>')
                    xml_lines.append(f'{indent}    <!-- (more items as needed) -->')
                else: # Array of primitives
                    placeholder_1 = self._generate_placeholder_value(ParameterDefinition(name=f"{param_name}_item_1", param_type=ParameterType.STRING, description="An item from the list."))
                    placeholder_2 = self._generate_placeholder_value(ParameterDefinition(name=f"{param_name}_item_2", param_type=ParameterType.STRING, description="An item from the list."))
                    xml_lines.append(f'{indent}    <item>{xml.sax.saxutils.escape(str(placeholder_1))}</item>')
                    xml_lines.append(f'{indent}    <item>{xml.sax.saxutils.escape(str(placeholder_2))}</item>')

                xml_lines.append(f'{indent}</arg>')
            
            else: # Primitive types
                placeholder_value = self._generate_placeholder_value(param_def)
                escaped_value = xml.sax.saxutils.escape(str(placeholder_value))
                xml_lines.append(f'{indent}<arg name="{param_name}">{escaped_value}</arg>')
        
        return xml_lines
