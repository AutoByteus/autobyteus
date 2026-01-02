import pytest 
from typing import Dict, Optional, Any

from autobyteus.tools.base_tool import BaseTool
from autobyteus.utils.parameter_schema import ParameterSchema, ParameterDefinition, ParameterType

def _parameter_type_to_json_schema_type(param_type: ParameterType) -> str:
    """Helper to convert ParameterType to a JSON schema type string."""
    type_map = {
        ParameterType.STRING: "string",
        ParameterType.INTEGER: "integer",
        ParameterType.FLOAT: "number",
        ParameterType.BOOLEAN: "boolean",
        ParameterType.OBJECT: "object",
        ParameterType.ARRAY: "array",
        ParameterType.ENUM: "string", # Enums are typically represented as strings
    }
    return type_map.get(param_type, "string") # Default to string

class MockTool(BaseTool):
    """A configurable mock tool for testing system prompt processing."""
    _class_level_name = "MockToolClassDefaultName"
    _class_level_description = "Mock tool class default description."
    _class_level_args_schema: Optional[ParameterSchema] = None

    def __init__(self, 
                 name: str, 
                 description: str, 
                 args_schema: Optional[ParameterSchema] = None, 
                 xml_output: Optional[str] = None,
                 json_output: Optional[Dict[str, Any]] = None,
                 execute_should_raise: Optional[Exception] = None,
                 xml_should_raise: Optional[Exception] = None,
                 json_should_raise: Optional[Exception] = None):
        self._instance_name = name
        self._instance_description = description
        self._instance_args_schema = args_schema
        self._xml_output = xml_output
        self._json_output = json_output
        self._execute_should_raise = execute_should_raise
        self._xml_should_raise = xml_should_raise
        self._json_should_raise = json_should_raise
        
        super().__init__()

    @classmethod
    def get_name(cls) -> str:
        return cls._class_level_name

    @classmethod
    def get_description(cls) -> str:
        return cls._class_level_description
    
    @classmethod
    def get_argument_schema(cls) -> Optional[ParameterSchema]:
        return cls._class_level_args_schema

    def tool_usage_xml(self) -> str: 
        if self._xml_should_raise:
            raise self._xml_should_raise
        if self._xml_output is not None:
            return self._xml_output
        
        # Use BaseTool's default implementation if no override is provided
        return super().tool_usage_xml()

    def tool_usage_json(self) -> Dict[str, Any]:
        """Generates a JSON-like dictionary representing the tool's schema."""
        if self._json_should_raise:
            raise self._json_should_raise
        if self._json_output is not None:
            return self._json_output

        # Re-implement a simplified version of BaseTool's logic since we can't call it directly
        # without a circular dependency or more complex mocking.
        schema_to_use = self._instance_args_schema
        
        json_schema: Dict[str, Any] = {
            "name": self._instance_name,
            "description": self._instance_description,
            "input_schema": {
                "type": "object",
                "properties": {},
            }
        }
        
        required_params = []
        if schema_to_use and schema_to_use.parameters:
            for param_def in schema_to_use.parameters:
                param_info: Dict[str, Any] = {
                    "type": _parameter_type_to_json_schema_type(param_def.param_type),
                    "description": param_def.description
                }
                if param_def.enum_values:
                    param_info["enum"] = param_def.enum_values
                if param_def.default_value is not None:
                    param_info["default"] = param_def.default_value
                
                json_schema["input_schema"]["properties"][param_def.name] = param_info
                if param_def.required:
                    required_params.append(param_def.name)
        
        if required_params:
            json_schema["input_schema"]["required"] = required_params

        return json_schema

    async def _execute(self, context: Optional[Any] = None, **kwargs: Any) -> Any: 
        if self._execute_should_raise:
            raise self._execute_should_raise
        return f"MockTool '{self._instance_name}' executed with {kwargs}"
