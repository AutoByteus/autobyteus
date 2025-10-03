# file: autobyteus/autobyteus/utils/parameter_schema.py
from __future__ import annotations
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
    OBJECT = "object"
    ARRAY = "array"

    def to_json_schema_type(self) -> str:
        """Maps parameter type to JSON schema type."""
        if self == ParameterType.FLOAT:
            return "number"
        if self == ParameterType.ENUM:
            return "string"
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
    # FIX: Allow dict for raw JSON schemas, in addition to ParameterType and ParameterSchema.
    array_item_schema: Optional[Union[ParameterType, ParameterSchema, dict]] = None
    object_schema: Optional[ParameterSchema] = None

    def __post_init__(self):
        if not self.name or not isinstance(self.name, str):
            raise ValueError("ParameterDefinition name must be a non-empty string")
        
        if not self.description or not isinstance(self.description, str):
            raise ValueError(f"ParameterDefinition '{self.name}' must have a non-empty description")
        
        if self.param_type == ParameterType.ENUM and not self.enum_values:
            raise ValueError(f"ParameterDefinition '{self.name}' of type ENUM must specify enum_values")
        
        # FIX: Update validation to allow dict for array_item_schema.
        if self.array_item_schema is not None and not isinstance(self.array_item_schema, (ParameterType, ParameterSchema, dict)):
            raise ValueError(f"ParameterDefinition '{self.name}': array_item_schema must be a ParameterType, ParameterSchema, or dict instance.")

        if self.object_schema is not None and not isinstance(self.object_schema, ParameterSchema):
            raise ValueError(f"ParameterDefinition '{self.name}': object_schema must be a ParameterSchema instance.")
            
        if self.param_type == ParameterType.ARRAY and self.array_item_schema is None:
            logger.debug(f"ParameterDefinition '{self.name}' of type ARRAY has no item schema. Will be a generic array of any type.")

        if self.param_type != ParameterType.ARRAY and self.array_item_schema is not None:
            raise ValueError(f"ParameterDefinition '{self.name}': array_item_schema should only be provided if param_type is ARRAY.")

        if self.param_type != ParameterType.OBJECT and self.object_schema is not None:
            raise ValueError(f"ParameterDefinition '{self.name}': object_schema should only be provided if param_type is OBJECT.")

        if self.required and self.default_value is not None:
            logger.debug(f"ParameterDefinition '{self.name}' is marked as required but has a default value. This is acceptable.")

    def validate_value(self, value: Any) -> bool:
        if value is None: 
            return not self.required 

        if self.param_type == ParameterType.STRING:
            if not isinstance(value, str): return False
            if self.pattern and not re.match(self.pattern, value): return False 
        
        elif self.param_type == ParameterType.INTEGER:
            if not isinstance(value, int) or isinstance(value, bool): return False
            if self.min_value is not None and value < self.min_value: return False
            if self.max_value is not None and value > self.max_value: return False
        
        elif self.param_type == ParameterType.FLOAT:
            if not isinstance(value, (float, int)): return False
            if self.min_value is not None and float(value) < self.min_value: return False
            if self.max_value is not None and float(value) > self.max_value: return False
        
        elif self.param_type == ParameterType.BOOLEAN:
            if not isinstance(value, bool): return False
        
        elif self.param_type == ParameterType.ENUM:
            if not isinstance(value, str) or value not in (self.enum_values or []): return False
        
        elif self.param_type == ParameterType.OBJECT:
            if not isinstance(value, dict): return False
        
        elif self.param_type == ParameterType.ARRAY:
            if not isinstance(value, list): return False

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
        # FIX: Correctly serialize dicts for array_item_schema.
        if self.param_type == ParameterType.ARRAY and self.array_item_schema is not None:
            if isinstance(self.array_item_schema, ParameterSchema):
                data["array_item_schema"] = self.array_item_schema.to_dict()
            elif isinstance(self.array_item_schema, dict):
                data["array_item_schema"] = self.array_item_schema
            elif isinstance(self.array_item_schema, ParameterType):
                data["array_item_schema"] = {"type": self.array_item_schema.value}

        if self.param_type == ParameterType.OBJECT and self.object_schema is not None:
            data["object_schema"] = self.object_schema.to_dict()
        return data

    def to_json_schema_property_dict(self) -> Dict[str, Any]:
        if self.param_type == ParameterType.OBJECT and self.object_schema:
            schema = self.object_schema.to_json_schema_dict()
            schema["description"] = self.description
            return schema

        prop_dict: Dict[str, Any] = {
            "type": self.param_type.to_json_schema_type(),
            "description": self.description,
        }
        if self.default_value is not None:
            prop_dict["default"] = self.default_value
        
        if self.param_type == ParameterType.ENUM and self.enum_values:
            prop_dict["enum"] = self.enum_values
        
        if self.min_value is not None and self.param_type in [ParameterType.INTEGER, ParameterType.FLOAT]:
            prop_dict["minimum"] = self.min_value
        
        if self.max_value is not None and self.param_type in [ParameterType.INTEGER, ParameterType.FLOAT]:
            prop_dict["maximum"] = self.max_value
        
        if self.pattern and self.param_type == ParameterType.STRING:
            prop_dict["pattern"] = self.pattern
            
        # FIX: Correctly handle dicts when generating the 'items' part of an array schema.
        if self.param_type == ParameterType.ARRAY:
            if isinstance(self.array_item_schema, ParameterSchema):
                prop_dict["items"] = self.array_item_schema.to_json_schema_dict()
            elif isinstance(self.array_item_schema, dict):
                prop_dict["items"] = self.array_item_schema
            elif isinstance(self.array_item_schema, ParameterType):
                prop_dict["items"] = {"type": self.array_item_schema.to_json_schema_type()}
            else:
                prop_dict["items"] = True 
        
        return prop_dict

@dataclass
class ParameterSchema:
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
                logger.debug(f"Unknown parameter '{key}' provided. It will be ignored.")
                continue 
            if not param_def.validate_value(value):
                errors.append(f"Invalid value for parameter '{param_def.name}': '{str(value)[:50]}...'. Expected type compatible with {param_def.param_type.value}.")
        return len(errors) == 0, errors

    def to_dict(self) -> Dict[str, Any]:
        return {"parameters": [param.to_dict() for param in self.parameters]}

    def to_json_schema_dict(self) -> Dict[str, Any]:
        if not self.parameters:
             return {"type": "object", "properties": {}, "required": []}
        properties = {p.name: p.to_json_schema_property_dict() for p in self.parameters}
        required = [p.name for p in self.parameters if p.required]
        return {"type": "object", "properties": properties, "required": required}

    @classmethod
    def from_dict(cls, schema_data: Dict[str, Any]) -> 'ParameterSchema':
        schema = cls()
        for param_data in schema_data.get("parameters", []):
            try:
                param_type_enum = ParameterType(param_data["type"])
            except ValueError:
                raise ValueError(f"Invalid parameter type string '{param_data['type']}' for param '{param_data.get('name')}'.")
            
            array_schema_obj = None
            if "array_item_schema" in param_data and param_data["array_item_schema"] is not None:
                item_schema_data = param_data["array_item_schema"]
                
                # FIX: Add robust logic to deserialize array_item_schema correctly.
                if isinstance(item_schema_data, dict):
                    if "parameters" in item_schema_data:
                        # It's our internal ParameterSchema format.
                        array_schema_obj = ParameterSchema.from_dict(item_schema_data)
                    elif "type" in item_schema_data and len(item_schema_data) == 1:
                        # Heuristic: it's a simple primitive type like {'type': 'string'}.
                        try:
                            array_schema_obj = ParameterType(item_schema_data["type"])
                        except ValueError:
                            # Not a valid ParameterType, so treat it as a raw schema dict.
                            array_schema_obj = item_schema_data
                    else:
                        # It's a complex JSON schema dict, store it as is.
                        array_schema_obj = item_schema_data
                else:
                    # Should not be hit if serialized with to_dict, but handle for robustness.
                    array_schema_obj = item_schema_data

            object_schema_obj = None
            if "object_schema" in param_data and param_data["object_schema"] is not None:
                object_schema_obj = ParameterSchema.from_dict(param_data["object_schema"])
                
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
                array_item_schema=array_schema_obj,
                object_schema=object_schema_obj
            )
            schema.add_parameter(param)
        return schema

    def __len__(self) -> int:
        return len(self.parameters)

    def __bool__(self) -> bool:
        return bool(self.parameters)
