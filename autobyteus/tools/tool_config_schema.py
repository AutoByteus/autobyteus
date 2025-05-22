# file: autobyteus/autobyteus/tools/tool_config_schema.py
import logging
from typing import Dict, Any, List, Optional, Union, Type
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)

class ParameterType(str, Enum):
    """Enumeration of supported parameter types for tool configuration."""
    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    ENUM = "enum"
    FILE_PATH = "file_path"
    DIRECTORY_PATH = "directory_path"

@dataclass
class ToolConfigParameter:
    """
    Represents a single configuration parameter for a tool.
    """
    name: str
    param_type: ParameterType
    description: str
    required: bool = False
    default_value: Any = None
    enum_values: Optional[List[str]] = None
    min_value: Optional[Union[int, float]] = None
    max_value: Optional[Union[int, float]] = None
    pattern: Optional[str] = None  # For string validation
    
    def __post_init__(self):
        """Validate parameter definition after initialization."""
        if not self.name or not isinstance(self.name, str):
            raise ValueError("Parameter name must be a non-empty string")
        
        if not self.description or not isinstance(self.description, str):
            raise ValueError(f"Parameter '{self.name}' must have a non-empty description")
        
        if self.param_type == ParameterType.ENUM and not self.enum_values:
            raise ValueError(f"Parameter '{self.name}' of type ENUM must specify enum_values")
        
        if self.required and self.default_value is not None:
            logger.warning(f"Parameter '{self.name}' is marked as required but has a default value")

    def validate_value(self, value: Any) -> bool:
        """
        Validate that a value conforms to this parameter's constraints.
        
        Args:
            value: The value to validate.
            
        Returns:
            bool: True if valid, False otherwise.
        """
        if value is None:
            return not self.required
        
        # Type validation
        if self.param_type == ParameterType.STRING:
            if not isinstance(value, str):
                return False
            if self.pattern:
                import re
                return bool(re.match(self.pattern, value))
        
        elif self.param_type == ParameterType.INTEGER:
            if not isinstance(value, int):
                return False
            if self.min_value is not None and value < self.min_value:
                return False
            if self.max_value is not None and value > self.max_value:
                return False
        
        elif self.param_type == ParameterType.FLOAT:
            if not isinstance(value, (int, float)):
                return False
            if self.min_value is not None and value < self.min_value:
                return False
            if self.max_value is not None and value > self.max_value:
                return False
        
        elif self.param_type == ParameterType.BOOLEAN:
            if not isinstance(value, bool):
                return False
        
        elif self.param_type == ParameterType.ENUM:
            if not isinstance(value, str) or value not in self.enum_values:
                return False
        
        elif self.param_type in [ParameterType.FILE_PATH, ParameterType.DIRECTORY_PATH]:
            if not isinstance(value, str):
                return False
        
        return True

    def to_dict(self) -> Dict[str, Any]:
        """Convert parameter to dictionary representation for JSON serialization."""
        return {
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

@dataclass
class ToolConfigSchema:
    """
    Describes the complete configuration schema for a tool.
    """
    parameters: List[ToolConfigParameter] = field(default_factory=list)
    
    def add_parameter(self, parameter: ToolConfigParameter) -> None:
        """Add a parameter to the schema."""
        if not isinstance(parameter, ToolConfigParameter):
            raise TypeError("parameter must be a ToolConfigParameter instance")
        
        # Check for duplicates
        if any(p.name == parameter.name for p in self.parameters):
            raise ValueError(f"Parameter '{parameter.name}' already exists in schema")
        
        self.parameters.append(parameter)

    def get_parameter(self, name: str) -> Optional[ToolConfigParameter]:
        """Get a parameter by name."""
        return next((p for p in self.parameters if p.name == name), None)

    def validate_config(self, config_data: Dict[str, Any]) -> tuple[bool, List[str]]:
        """
        Validate a configuration dictionary against this schema.
        
        Args:
            config_data: The configuration to validate.
            
        Returns:
            tuple: (is_valid, list_of_error_messages)
        """
        errors = []
        
        # Check required parameters
        for param in self.parameters:
            if param.required and param.name not in config_data:
                errors.append(f"Required parameter '{param.name}' is missing")
            elif param.name in config_data:
                if not param.validate_value(config_data[param.name]):
                    errors.append(f"Invalid value for parameter '{param.name}': {config_data[param.name]}")
        
        # Check for unknown parameters
        schema_param_names = {p.name for p in self.parameters}
        for key in config_data:
            if key not in schema_param_names:
                errors.append(f"Unknown parameter '{key}'")
        
        return len(errors) == 0, errors

    def get_defaults(self) -> Dict[str, Any]:
        """Get default values for all parameters that have them."""
        return {
            param.name: param.default_value 
            for param in self.parameters 
            if param.default_value is not None
        }

    def to_dict(self) -> Dict[str, Any]:
        """Convert schema to dictionary representation for JSON serialization."""
        return {
            "parameters": [param.to_dict() for param in self.parameters]
        }

    @classmethod
    def from_dict(cls, schema_data: Dict[str, Any]) -> 'ToolConfigSchema':
        """Create a ToolConfigSchema from dictionary representation."""
        schema = cls()
        
        for param_data in schema_data.get("parameters", []):
            param = ToolConfigParameter(
                name=param_data["name"],
                param_type=ParameterType(param_data["type"]),
                description=param_data["description"],
                required=param_data.get("required", False),
                default_value=param_data.get("default_value"),
                enum_values=param_data.get("enum_values"),
                min_value=param_data.get("min_value"),
                max_value=param_data.get("max_value"),
                pattern=param_data.get("pattern"),
            )
            schema.add_parameter(param)
        
        return schema

    def __len__(self) -> int:
        return len(self.parameters)

    def __bool__(self) -> bool:
        return len(self.parameters) > 0
