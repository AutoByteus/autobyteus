# file: autobyteus/autobyteus/agent/system_prompt_processor/tool_usage_example_injector_processor.py
import logging
from typing import Dict, List, TYPE_CHECKING, Any
import xml.sax.saxutils # For escaping attribute values in examples
import json # For formatting JSON examples

from .base_processor import BaseSystemPromptProcessor
from autobyteus.tools.parameter_schema import ParameterType # For checking param type

if TYPE_CHECKING:
    from autobyteus.tools.base_tool import BaseTool
    from autobyteus.tools.parameter_schema import ParameterDefinition
    from autobyteus.agent.context import AgentContext 

logger = logging.getLogger(__name__)

class ToolUsageExampleInjectorProcessor(BaseSystemPromptProcessor):
    """
    A system prompt processor that injects concrete examples of tool usage
    into the system prompt, in either XML or JSON format based on the
    AgentSpecification's 'use_xml_tool_format' flag.
    It looks for a `{{tool_examples}}` placeholder.
    """
    PLACEHOLDER = "{{tool_examples}}"
    DEFAULT_NO_TOOLS_MESSAGE = "This agent currently has no tools with usage examples available."
    # Headers will be chosen based on the format
    XML_EXAMPLES_HEADER = "Tool Usage Examples (XML Format):\n"
    JSON_EXAMPLES_HEADER = "Tool Usage Examples (JSON Format):\n"


    @classmethod
    def get_name(cls) -> str:
        return "ToolUsageExampleInjector"

    def _generate_placeholder_value(self, param_def: 'ParameterDefinition') -> Any:
        """
        Generates a plausible Python native placeholder value for a given parameter definition.
        This value will then be converted to string for XML or used directly for JSON.
        """
        if param_def.default_value is not None:
            return param_def.default_value 
        
        param_type = param_def.param_type
        param_name_lower = param_def.name.lower()

        if param_type == ParameterType.STRING:
            # Heuristics based on parameter name for better examples. Order matters.
            if "directory" in param_name_lower or "dir_path" in param_name_lower:
                return "/path/to/example/directory/"
            if "path" in param_name_lower or "file" in param_name_lower:
                return "/path/to/example.txt"
            if "query" in param_name_lower: return "example search query"
            if "url" in param_name_lower: return "https://example.com"
            if "content" in param_name_lower: return "Example text content."
            if "description" in param_name_lower: return "A brief description."
            if "message" in param_name_lower: return "Your message here."
            return "example_string_value"
        elif param_type == ParameterType.INTEGER:
            return 123
        elif param_type == ParameterType.FLOAT:
            return 123.45
        elif param_type == ParameterType.BOOLEAN:
            return True 
        elif param_type == ParameterType.ENUM:
            return param_def.enum_values[0] if param_def.enum_values else "enum_value"
        elif param_type == ParameterType.OBJECT:
            return {"key1": "example_value", "key2": 100} 
        elif param_type == ParameterType.ARRAY:
            return ["example_item1", 2, True] 
        return "placeholder_value"

    def _generate_tool_example_xml(self, tool_instance: 'BaseTool') -> str:
        tool_name = tool_instance.get_name()
        arg_schema = tool_instance.get_argument_schema()

        example_xml_parts = [f'<command name="{tool_name}">']
        
        params_included_in_example = False
        if arg_schema and arg_schema.parameters:
            for param_def in arg_schema.parameters:
                if param_def.required or param_def.default_value is not None:
                    placeholder_py_value = self._generate_placeholder_value(param_def)
                    placeholder_str_value = str(placeholder_py_value)
                    if isinstance(placeholder_py_value, bool):
                         placeholder_str_value = 'true' if placeholder_py_value else 'false'

                    escaped_placeholder = xml.sax.saxutils.escape(placeholder_str_value)
                    example_xml_parts.append(f'    <arg name="{param_def.name}">{escaped_placeholder}</arg>')
                    params_included_in_example = True
            
            if not params_included_in_example and arg_schema.parameters: 
                 example_xml_parts.append("    <!-- This tool has arguments, but none are shown in this basic example. Refer to the tool's description/schema for full details. -->")
        
        if not arg_schema or not arg_schema.parameters: 
            example_xml_parts.append("    <!-- This tool takes no arguments. -->")
            
        example_xml_parts.append("</command>")
        return "\n".join(example_xml_parts)

    def _generate_tool_example_json_obj(self, tool_instance: 'BaseTool') -> Dict[str, Any]:
        """Generates a Python dictionary representing a JSON tool call example."""
        tool_name = tool_instance.get_name()
        arg_schema = tool_instance.get_argument_schema()

        arguments_dict: Dict[str, Any] = {}
        if arg_schema and arg_schema.parameters:
            for param_def in arg_schema.parameters:
                if param_def.required or param_def.default_value is not None:
                    placeholder_py_value = self._generate_placeholder_value(param_def)
                    arguments_dict[param_def.name] = placeholder_py_value
        
        return {
            "tool_name": tool_name,
            "arguments": arguments_dict
        }

    def process(self,
                system_prompt: str,
                tool_instances: Dict[str, 'BaseTool'],
                agent_id: str,
                context: 'AgentContext'
               ) -> str:
        if self.PLACEHOLDER not in system_prompt:
            logger.debug(f"{self.get_name()}: Placeholder '{self.PLACEHOLDER}' not found in system prompt for agent '{agent_id}'. Prompt unchanged.")
            return system_prompt

        if not tool_instances:
            logger.info(f"{self.get_name()}: No tools available for agent '{agent_id}'. Replacing placeholder with: '{self.DEFAULT_NO_TOOLS_MESSAGE}'")
            return system_prompt.replace(self.PLACEHOLDER, self.DEFAULT_NO_TOOLS_MESSAGE)

        use_xml_format = context.specification.use_xml_tool_format
        example_snippets: List[str] = []
        chosen_format_str = "XML" if use_xml_format else "JSON"
        
        section_header: str
        if use_xml_format:
            section_header = self.XML_EXAMPLES_HEADER
        else:
            section_header = self.JSON_EXAMPLES_HEADER

        for tool_name, tool_instance in tool_instances.items():
            try:
                if use_xml_format:
                    xml_ex = self._generate_tool_example_xml(tool_instance)
                    example_snippets.append(xml_ex)
                else: # JSON format
                    json_ex_obj = self._generate_tool_example_json_obj(tool_instance)
                    json_ex_str = json.dumps(json_ex_obj, indent=2) # Indent with 2 spaces for JSON examples
                    example_snippets.append(json_ex_str)

            except Exception as e:
                logger.error(f"{self.get_name()}: Failed to generate {chosen_format_str} example for tool '{tool_name}' for agent '{agent_id}': {e}", exc_info=True)
                if use_xml_format:
                    example_snippets.append(f"<!-- Error generating XML example for tool: {xml.sax.saxutils.escape(tool_name)} -->")
                else:
                    example_snippets.append(f"// Error generating JSON example for tool: {tool_name}")
        
        if not example_snippets: 
            logger.warning(f"{self.get_name()}: Tool instances present for agent '{agent_id}', but no {chosen_format_str} examples were generated. Using default no tools message.")
            return system_prompt.replace(self.PLACEHOLDER, self.DEFAULT_NO_TOOLS_MESSAGE)

        # Construct the full examples section
        full_examples_section_parts = [section_header]
        full_examples_section_parts.extend(example_snippets)
        
        all_examples_str = "\n\n".join(full_examples_section_parts) # Use double newline between header and first example, and between examples
        
        final_system_prompt = system_prompt.replace(self.PLACEHOLDER, all_examples_str)
        logger.info(f"{self.get_name()}: System prompt for agent '{agent_id}' processed. Placeholder '{self.PLACEHOLDER}' replaced with {chosen_format_str} tool usage examples.")
        return final_system_prompt
