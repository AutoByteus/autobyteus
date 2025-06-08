# file: autobyteus/autobyteus/tools/parameter_schema.py
import logging
from typing import Dict, Any, List, Optional, Union, Type
from dataclasses import dataclass, field
from enum import Enum
import re # For pattern validation

logger = logging.getLogger(__name__)

class ParameterType(str, Enum):
    """Enumeration of supported parameter types for tool configuration."""
    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    ENUM = "enum"
    # FILE_PATH = "file_path" # REMOVED
    # DIRECTORY_PATH = "directory_path" # REMOVED
    OBJECT = "object"
    ARRAY = "array"

    def to_json_schema_type(self) -> str:
        """Maps parameter type to JSON schema type."""
        if self == ParameterType.FLOAT:
            return "number"
        # REMOVED: FILE_PATH and DIRECTORY_PATH handling, ENUM still maps to string
        if self == ParameterType.ENUM:
            return "string"
        # For OBJECT and ARRAY, their value is already the correct JSON schema type
        # STRING, INTEGER, BOOLEAN also map directly to their values.
        if self in [ParameterType.OBJECT, ParameterType.ARRAY, ParameterType.STRING, ParameterType.INTEGER, ParameterType.BOOLEAN]:
            return self.value
        return self.value # Fallback, should be covered by above

@dataclass
class ParameterDefinition:
    """
    Represents a single parameter definition for a tool's arguments or configuration.
    """
    name: str
    param_type: ParameterType
    description: str
    required: bool = False
    default_value: Any = None
    enum_values: Optional[List[str]] = None
    min_value: Optional[Union[int, float]] = None
    max_value: Optional[Union[int, float]] = None
    pattern: Optional[str] = None
    array_item_schema: Optional[Dict[str, Any]] = None 
    
    def __post_init__(self):
        if not self.name or not isinstance(self.name, str):
            raise ValueError("ParameterDefinition name must be a non-empty string")
        
        if not self.description or not isinstance(self.description, str):
            raise ValueError(f"ParameterDefinition '{self.name}' must have a non-empty description")
        
        if self.param_type == ParameterType.ENUM and not self.enum_values:
            raise ValueError(f"ParameterDefinition '{self.name}' of type ENUM must specify enum_values")
        
        if self.param_type == ParameterType.ARRAY and self.array_item_schema is None:
            logger.debug(f"ParameterDefinition '{self.name}' of type ARRAY has no array_item_schema. Will be represented as a generic array.")

        if self.param_type != ParameterType.ARRAY and self.array_item_schema is not None:
            raise ValueError(f"ParameterDefinition '{self.name}': array_item_schema should only be provided if param_type is ARRAY.")

        if self.required and self.default_value is not None:
            logger.debug(f"ParameterDefinition '{self.name}' is marked as required but has a default value. This is acceptable.")

    def validate_value(self, value: Any) -> bool:
        if value is None: 
            return not self.required 

        if self.param_type == ParameterType.STRING:
            if not isinstance(value, str):
                return False
            if self.pattern:
                if not re.match(self.pattern, value):
                    return False 
        
        elif self.param_type == ParameterType.INTEGER:
            if not isinstance(value, int): 
                if isinstance(value, bool): return False
                return False
            if self.min_value is not None and value < self.min_value:
                return False
            if self.max_value is not None and value > self.max_value:
                return False
        
        elif self.param_type == ParameterType.FLOAT:
            if not isinstance(value, (float, int)): 
                return False
            if self.min_value is not None and float(value) < self.min_value:
                return False
            if self.max_value is not None and float(value) > self.max_value:
                return False
        
        elif self.param_type == ParameterType.BOOLEAN:
            if not isinstance(value, bool):
                return False
        
        elif self.param_type == ParameterType.ENUM:
            if not isinstance(value, str) or value not in (self.enum_values or []):
                return False
        
        # REMOVED: Specific validation for FILE_PATH, DIRECTORY_PATH (they are now STRING)
        
        elif self.param_type == ParameterType.OBJECT:
            if not isinstance(value, dict):
                return False
        
        elif self.param_type == ParameterType.ARRAY:
            if not isinstance(value, list):
                return False

        return True

    def to_dict(self) -> Dict[str, Any]:
        data = {
            "name": self.name,
            "type": self.param_type.value,
            "description": self.description,
            "required": self.required,
            "default_value": self.default_value,
            "enum_values": self.enum_values,
            "min_value": self.min_value,
            "max_value": self.max_value,
            "pattern": self.pattern,
        }
        if self.param_type == ParameterType.ARRAY and self.array_item_schema is not None:
            data["array_item_schema"] = self.array_item_schema
        return data

    def to_json_schema_property_dict(self) -> Dict[str, Any]:
        prop_dict: Dict[str, Any] = {
            "type": self.param_type.to_json_schema_type(),
            "description": self.description,
        }
        if self.default_value is not None:
            prop_dict["default"] = self.default_value
        
        if self.param_type == ParameterType.ENUM and self.enum_values:
            prop_dict["enum"] = self.enum_values
        
        if self.min_value is not None:
            if self.param_type in [ParameterType.INTEGER, ParameterType.FLOAT]:
                prop_dict["minimum"] = self.min_value
        
        if self.max_value is not None:
            if self.param_type in [ParameterType.INTEGER, ParameterType.FLOAT]:
                prop_dict["maximum"] = self.max_value
        
        # REMOVED: Pattern check specific to FILE_PATH/DIRECTORY_PATH as they are now STRING
        if self.pattern and self.param_type == ParameterType.STRING:
            prop_dict["pattern"] = self.pattern
            
        if self.param_type == ParameterType.ARRAY:
            if self.array_item_schema is not None:
                prop_dict["items"] = self.array_item_schema
            else:
                prop_dict["items"] = True 
                logger.debug(f"Parameter '{self.name}' is ARRAY type with no item schema; JSON schema 'items' will be generic.")
        
        return prop_dict

@dataclass
class ParameterSchema:
    """
    Describes a schema for a set of parameters, either for tool arguments or instantiation configuration.
    """
    parameters: List[ParameterDefinition] = field(default_factory=list)
    
    def add_parameter(self, parameter: ParameterDefinition) -> None:
        if not isinstance(parameter, ParameterDefinition):
            raise TypeError("parameter must be a ParameterDefinition instance")
        
        if any(p.name == parameter.name for p in self.parameters):
            raise ValueError(f"Parameter '{parameter.name}' already exists in schema")
        
        self.parameters.append(parameter)

    def get_parameter(self, name: str) -> Optional[ParameterDefinition]:
        return next((p for p in self.parameters if p.name == name), None)

    def validate_config(self, config_data: Dict[str, Any]) -> tuple[bool, List[str]]:
        errors = []
        
        for param_def in self.parameters:
            if param_def.required and param_def.name not in config_data:
                errors.append(f"Required parameter '{param_def.name}' is missing.")
        
        for key, value in config_data.items():
            param_def = self.get_parameter(key)
            if not param_def:
                logger.debug(f"Unknown parameter '{key}' provided. It will be ignored by schema-based processing but passed through if possible.")
                continue 
            
            if not param_def.validate_value(value):
                errors.append(f"Invalid value for parameter '{param_def.name}': '{str(value)[:50]}...'. Expected type compatible with {param_def.param_type.value}.")

        return len(errors) == 0, errors

    def get_defaults(self) -> Dict[str, Any]:
        return {
            param.name: param.default_value 
            for param in self.parameters 
            if param.default_value is not None
        }

    def to_dict(self) -> Dict[str, Any]:
        return {
            "parameters": [param.to_dict() for param in self.parameters]
        }

    def to_json_schema_dict(self) -> Dict[str, Any]:
        if not self.parameters:
             return {
                "type": "object",
                "properties": {},
                "required": []
            }

        properties = {
            param.name: param.to_json_schema_property_dict()
            for param in self.parameters
        }
        required = [
            param.name for param in self.parameters if param.required
        ]
        
        return {
            "type": "object",
            "properties": properties,
            "required": required,
        }

    @classmethod
    def from_dict(cls, schema_data: Dict[str, Any]) -> 'ParameterSchema':
        schema = cls()
        
        for param_data in schema_data.get("parameters", []):
            param_type_value = param_data["type"]
            try:
                param_type_enum = ParameterType(param_type_value)
            except ValueError:
                raise ValueError(f"Invalid parameter type string '{param_type_value}' in schema data for parameter '{param_data.get('name')}'.")

            param = ParameterDefinition(
                name=param_data["name"],
                param_type=param_type_enum,
                description=param_data["description"],
                required=param_data.get("required", False),
                default_value=param_data.get("default_value"),
                enum_values=param_data.get("enum_values"),
                min_value=param_data.get("min_value"),
                max_value=param_data.get("max_value"),
                pattern=param_data.get("pattern"),
                array_item_schema=param_data.get("array_item_schema") 
            )
            schema.add_parameter(param)
        
        return schema

    def __len__(self) -> int:
        return len(self.parameters)

    def __bool__(self) -> bool:
        return len(self.parameters) > 0
