# file: autobyteus/tools/registry/tool_definition.py
import logging
from typing import Dict, Any, List as TypingList, Type, TYPE_CHECKING, Optional, Callable

if TYPE_CHECKING:
    from autobyteus.tools.base_tool import BaseTool
    from autobyteus.tools.tool_config import ToolConfig
    from autobyteus.tools.parameter_schema import ParameterSchema

logger = logging.getLogger(__name__)

class ToolDefinition:
    """
    Represents the definition of a tool, containing its metadata and the means
    to create an instance, either via a tool_class or a custom_factory.
    """
    def __init__(self,
                 name: str,
                 description: str,
                 argument_schema: Optional['ParameterSchema'],
                 usage_xml: str,
                 usage_json_dict: Dict[str, Any],
                 config_schema: Optional['ParameterSchema'] = None,
                 tool_class: Optional[Type['BaseTool']] = None,
                 custom_factory: Optional[Callable[['ToolConfig'], 'BaseTool']] = None):
        """
        Initializes the ToolDefinition.

        Args:
            name: The unique name of the tool.
            description: A description of what the tool does.
            argument_schema: Schema defining arguments for the tool's execute method.
            usage_xml: Pre-generated XML usage string.
            usage_json_dict: Pre-generated JSON usage dictionary (for function calling).
            config_schema: Optional schema describing the tool's instantiation parameters.
            tool_class: The class to instantiate for this tool (for standard tools).
            custom_factory: A factory function to call to create an instance (for dynamic tools).
        """
        if not name or not isinstance(name, str):
            raise ValueError("ToolDefinition requires a non-empty string 'name'.")
        if not description or not isinstance(description, str):
            raise ValueError(f"ToolDefinition '{name}' requires a non-empty string 'description'.")
        if not isinstance(usage_xml, str):
            raise ValueError(f"ToolDefinition '{name}' requires a string for 'usage_xml'.")
        if not isinstance(usage_json_dict, dict):
            raise ValueError(f"ToolDefinition '{name}' requires a dict for 'usage_json_dict'.")

        if tool_class is None and custom_factory is None:
            raise ValueError(f"ToolDefinition '{name}' must provide either a 'tool_class' or a 'custom_factory'.")
        if tool_class is not None and custom_factory is not None:
            raise ValueError(f"ToolDefinition '{name}' cannot have both a 'tool_class' and a 'custom_factory'.")
        
        if tool_class and not isinstance(tool_class, type):
            raise TypeError(f"ToolDefinition '{name}' requires a valid class for 'tool_class'.")
        if custom_factory and not callable(custom_factory):
            raise TypeError(f"ToolDefinition '{name}' requires a callable for 'custom_factory'.")

        from autobyteus.tools.parameter_schema import ParameterSchema
        if argument_schema is not None and not isinstance(argument_schema, ParameterSchema):
             raise TypeError(f"ToolDefinition '{name}' received an invalid 'argument_schema'. Expected ParameterSchema or None.")
        if config_schema is not None and not isinstance(config_schema, ParameterSchema):
             raise TypeError(f"ToolDefinition '{name}' received an invalid 'config_schema'. Expected ParameterSchema or None.")

        self._name = name
        self._description = description
        self._argument_schema: Optional['ParameterSchema'] = argument_schema
        self._usage_xml = usage_xml
        self._usage_json_dict = usage_json_dict
        self._config_schema: Optional['ParameterSchema'] = config_schema
        self._tool_class = tool_class
        self._custom_factory = custom_factory

        creator_info = f"class '{self.tool_class.__name__}'" if self.tool_class else "a custom factory"
        logger.debug(f"ToolDefinition created for tool '{self.name}' using {creator_info}.")

    @property
    def name(self) -> str:
        return self._name

    @property
    def description(self) -> str:
        return self._description

    @property
    def tool_class(self) -> Optional[Type['BaseTool']]:
        return self._tool_class
    
    @property
    def custom_factory(self) -> Optional[Callable[['ToolConfig'], 'BaseTool']]:
        return self._custom_factory

    @property
    def argument_schema(self) -> Optional['ParameterSchema']: 
        return self._argument_schema

    @property
    def usage_xml(self) -> str:
        return self._usage_xml

    @property
    def usage_json_dict(self) -> Dict[str, Any]: 
        return self._usage_json_dict

    @property
    def config_schema(self) -> Optional['ParameterSchema']: 
        return self._config_schema

    @property
    def has_instantiation_config(self) -> bool:
        return self._config_schema is not None and len(self._config_schema) > 0

    def validate_instantiation_config(self, config_data: Dict[str, Any]) -> tuple[bool, TypingList[str]]:
        if not self._config_schema:
            if config_data:
                return False, [f"Tool '{self.name}' does not accept instantiation configuration parameters"]
            return True, []
        
        return self._config_schema.validate_config(config_data)

    def get_default_instantiation_config(self) -> Dict[str, Any]:
        if not self._config_schema:
            return {}
        return self._config_schema.get_defaults()

    def __repr__(self) -> str:
        desc_repr = self.description
        if len(desc_repr) > 70:
             desc_repr = desc_repr[:67] + "..."
        desc_repr = desc_repr.replace('\n', '\\n').replace('\t', '\\t')
        
        creator_repr = f"class='{self._tool_class.__name__}'" if self._tool_class else "factory=True"
        return (f"ToolDefinition(name='{self.name}', {creator_repr}, "
                f"description='{desc_repr}')")

    def to_dict(self) -> Dict[str, Any]:
        result = {
            "name": self.name,
            "description": self.description,
            "tool_class_name": self.tool_class.__name__ if self.tool_class else None,
            "has_custom_factory": self.custom_factory is not None,
            "usage_xml": self.usage_xml,
            "usage_json_dict": self.usage_json_dict,
            "has_instantiation_config": self.has_instantiation_config,
        }
        
        if self.argument_schema:
            result["argument_schema_dict"] = self.argument_schema.to_dict() 
        else:
            result["argument_schema_dict"] = None
            
        if self.config_schema: 
            result["config_schema_dict"] = self.config_schema.to_dict() 
        else:
            result["config_schema_dict"] = None
            
        return result
