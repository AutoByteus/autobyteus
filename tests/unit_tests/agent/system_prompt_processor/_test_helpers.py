import pytest 
from typing import Dict, Optional, Any

from autobyteus.tools.base_tool import BaseTool
from autobyteus.tools.parameter_schema import ParameterSchema, ParameterDefinition, ParameterType

class MockTool(BaseTool):
    """A configurable mock tool for testing system prompt processing."""
    
    _class_level_name = "MockToolClassDefaultName"
    _class_level_description = "Mock tool class default description."

    def __init__(self, 
                 name: str, 
                 description: str, 
                 args_schema: Optional[ParameterSchema] = None, 
                 xml_output: Optional[str] = None,
                 json_output: Optional[Dict[str, Any]] = None, # ADDED for JSON schema
                 execute_should_raise: Optional[Exception] = None,
                 xml_should_raise: Optional[Exception] = None,
                 json_should_raise: Optional[Exception] = None): # ADDED for JSON schema error
        self._instance_name = name
        self._instance_description = description
        self._instance_args_schema = args_schema
        self._xml_output = xml_output
        self._json_output = json_output # ADDED
        self._execute_should_raise = execute_should_raise
        self._xml_should_raise = xml_should_raise
        self._json_should_raise = json_should_raise # ADDED
        
        super().__init__()

    @classmethod
    def get_name(cls) -> str:
        return cls._class_level_name
    
    @property 
    def name(self) -> str: 
        return self._instance_name

    @classmethod
    def get_description(cls) -> str:
        return cls._class_level_description

    @classmethod
    def get_argument_schema(cls) -> Optional[ParameterSchema]:
        default_schema = ParameterSchema() 
        default_schema.add_parameter(ParameterDefinition(
            name="mock_arg_class",
            param_type=ParameterType.STRING,
            description="A class-level mock argument.",
            required=False
        ))
        return default_schema

    def tool_usage_xml(self) -> str: 
        if self._xml_should_raise:
            raise self._xml_should_raise
        if self._xml_output is not None:
            return self._xml_output
        
        schema_to_use = self._instance_args_schema
        
        xml_parts = [f'<command name="{self._instance_name}" description="{self._instance_description}">']
        if schema_to_use and schema_to_use.parameters: 
            for param_def in schema_to_use.parameters: 
                xml_parts.append(f'  <arg name="{param_def.name}" type="{param_def.param_type.value}" required="{str(param_def.required).lower()}">{param_def.description}</arg>')
        else: 
            xml_parts.append('    <!-- This tool has no arguments or schema not provided for XML generation. -->')

        xml_parts.append('</command>')
        return "\n".join(xml_parts)

    def tool_usage_json(self) -> Dict[str, Any]: # ADDED method
        """Generates a JSON-like dictionary representing the tool's schema."""
        if self._json_should_raise:
            raise self._json_should_raise
        if self._json_output is not None:
            return self._json_output

        schema_to_use = self._instance_args_schema
        
        json_schema: Dict[str, Any] = {
            "name": self._instance_name,
            "description": self._instance_description,
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }

        if schema_to_use and schema_to_use.parameters:
            for param_def in schema_to_use.parameters:
                param_info: Dict[str, Any] = {
                    "type": param_def.param_type.to_json_schema_type(), # Assumes ParameterType has this method
                    "description": param_def.description
                }
                if param_def.enum_values:
                    param_info["enum"] = param_def.enum_values
                if param_def.default_value is not None:
                    param_info["default"] = param_def.default_value
                
                json_schema["parameters"]["properties"][param_def.name] = param_info
                if param_def.required:
                    json_schema["parameters"]["required"].append(param_def.name)
            if not json_schema["parameters"]["required"]: # OpenAI schema expects this field to be absent if no required params
                del json_schema["parameters"]["required"]
        else: # No args or schema_to_use.parameters is empty
             # For JSON schema, it's common to represent no arguments with an empty properties object
             pass


        return json_schema

    async def _execute(self, context: Optional[Any] = None, **kwargs: Any) -> Any: 
        if self._execute_should_raise:
            raise self._execute_should_raise
        return f"MockTool '{self._instance_name}' executed with {kwargs}"
