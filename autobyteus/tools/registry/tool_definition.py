# file: autobyteus/tools/registry/tool_definition.py
import logging
from typing import Dict, Any, List as TypingList, Type, TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from autobyteus.tools.base_tool import BaseTool
    from autobyteus.tools.parameter_schema import ParameterSchema # Updated import path

logger = logging.getLogger(__name__)

class ToolDefinition:
    """
    Represents the definition of a tool, containing its name, description,
    tool class reference, argument schema for execution, instantiation config schema,
    the generated XML usage string, and the generated JSON usage dictionary.
    """
    def __init__(self,
                 name: str,
                 description: str, 
                 tool_class: Type['BaseTool'],
                 argument_schema: Optional['ParameterSchema'], 
                 usage_xml: str, 
                 usage_json_dict: Dict[str, Any],
                 config_schema: Optional['ParameterSchema'] = None):
        """
        Initializes the ToolDefinition.
        Args:
            ...
            argument_schema: Schema defining arguments for the tool's execute method (ParameterSchema).
            ...
            config_schema: Optional schema describing the tool's instantiation (ParameterSchema).
        """
        if not name or not isinstance(name, str):
            raise ValueError("ToolDefinition requires a non-empty string 'name'.")
        if not description or not isinstance(description, str):
            raise ValueError(f"ToolDefinition '{name}' requires a non-empty string 'description'.")
        if not isinstance(tool_class, type):
            raise TypeError(f"ToolDefinition '{name}' requires a valid class for 'tool_class'.")
        if not isinstance(usage_xml, str):
            raise ValueError(f"ToolDefinition '{name}' requires a string for 'usage_xml'.")
        if not isinstance(usage_json_dict, dict):
            raise ValueError(f"ToolDefinition '{name}' requires a dict for 'usage_json_dict'.")
        
        # Ensure ParameterSchema is imported for isinstance check if not forward referenced
        # Assuming ParameterSchema is imported from .parameter_schema
        from autobyteus.tools.parameter_schema import ParameterSchema
        if argument_schema is not None and not isinstance(argument_schema, ParameterSchema):
             raise TypeError(f"ToolDefinition '{name}' received an invalid 'argument_schema'. Expected ParameterSchema or None.")
        if config_schema is not None and not isinstance(config_schema, ParameterSchema):
             raise TypeError(f"ToolDefinition '{name}' received an invalid 'config_schema'. Expected ParameterSchema or None.")


        self._name = name
        self._description = description
        self._tool_class = tool_class
        self._argument_schema: Optional['ParameterSchema'] = argument_schema
        self._usage_xml = usage_xml
        self._usage_json_dict = usage_json_dict
        self._config_schema: Optional['ParameterSchema'] = config_schema

        arg_schema_info = f"with {len(argument_schema)} execution arguments" if argument_schema else "takes no execution arguments"
        config_schema_info = f"with {len(config_schema)} instantiation config parameters" if config_schema else "no instantiation config"
        
        logger.debug(f"ToolDefinition created for tool '{self.name}' (class '{self.tool_class.__name__}'): {arg_schema_info}, {config_schema_info}.")

    @property
    def name(self) -> str:
        return self._name

    @property
    def description(self) -> str:
        return self._description

    @property
    def tool_class(self) -> Type['BaseTool']:
        return self._tool_class

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
        
        args_repr = f", args={len(self._argument_schema)}" if self._argument_schema else ", no_args"
        config_repr = f", inst_config={len(self._config_schema)}" if self._config_schema else ", no_inst_config"
        
        return (f"ToolDefinition(name='{self.name}', class='{self.tool_class.__name__}'{args_repr}{config_repr}, "
                f"description='{desc_repr}')")

    def to_dict(self) -> Dict[str, Any]:
        result = {
            "name": self.name,
            "description": self.description,
            "tool_class_name": self.tool_class.__name__,
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
