# File: autobyteus/autobyteus/tools/base_tool.py

import logging
from abc import ABC, abstractmethod
from typing import Optional, Any, TYPE_CHECKING, List as TypingList, Dict, Union

from autobyteus.events.event_emitter import EventEmitter
from autobyteus.utils.parameter_schema import ParameterType

from .tool_meta import ToolMeta
from .tool_state import ToolState

if TYPE_CHECKING:
    from autobyteus.agent.context import AgentContext
    from autobyteus.utils.parameter_schema import ParameterSchema, ParameterDefinition
    from autobyteus.tools.tool_config import ToolConfig
    from .tool_state import ToolState
    from autobyteus.tools.registry import ToolDefinition

logger = logging.getLogger('autobyteus')

class BaseTool(ABC, EventEmitter, metaclass=ToolMeta):
    """
    Abstract base class for all tools, with auto-registration via ToolMeta.
    """
    def __init__(self, config: Optional['ToolConfig'] = None):
        super().__init__()
        self.agent_id: Optional[str] = None
        self.definition: Optional['ToolDefinition'] = None
        self._config = config
        self.tool_state: 'ToolState' = ToolState()
        logger.debug(f"BaseTool instance initializing for potential class {self.__class__.__name__}. tool_state initialized.")

    @classmethod
    def get_name(cls) -> str:
        return cls.__name__
    
    @classmethod
    @abstractmethod
    def get_description(cls) -> str:
        raise NotImplementedError("Subclasses must implement get_description().")

    @classmethod
    @abstractmethod
    def get_argument_schema(cls) -> Optional['ParameterSchema']: 
        raise NotImplementedError("Subclasses must implement get_argument_schema().")

    @classmethod
    def get_config_schema(cls) -> Optional['ParameterSchema']: 
        return None

    def _coerce_argument_types(self, kwargs: Dict[str, Any]) -> Dict[str, Any]:
        """
        Coerces argument values from the parser (often strings) to their proper
        Python types based on the tool's argument schema.
        This method is fully recursive to handle nested objects and arrays.
        """
        arg_schema = self.get_argument_schema()
        if not arg_schema:
            return kwargs

        return self._coerce_object_recursively(kwargs, arg_schema)

    def _coerce_object_recursively(self, data: Dict[str, Any], schema: 'ParameterSchema') -> Dict[str, Any]:
        """ Helper to recursively coerce values in an object based on a ParameterSchema. """
        coerced_data = data.copy()
        for name, value in data.items():
            param_def = schema.get_parameter(name)
            if param_def:
                coerced_data[name] = self._coerce_value_recursively(value, param_def)
        return coerced_data

    def _coerce_value_recursively(self, value: Any, param_def: 'ParameterDefinition') -> Any:
        """ Coerces a single value based on its ParameterDefinition, recursing into complex types. """
        if value is None:
            return None

        # 1. Coerce empty string to empty list for ARRAY types. This is a common parser artifact.
        if param_def.param_type == ParameterType.ARRAY and value == "":
            return []

        # 2. Recurse into objects
        if param_def.param_type == ParameterType.OBJECT and param_def.object_schema and isinstance(value, dict):
            return self._coerce_object_recursively(value, param_def.object_schema)

        # 3. Recurse into arrays.
        if param_def.param_type == ParameterType.ARRAY and isinstance(value, list):
            item_schema_dict = param_def.array_item_schema
            # If items are objects described by a schema, coerce each one.
            if item_schema_dict and isinstance(item_schema_dict, dict) and item_schema_dict.get("type") == "object":
                # Create a temporary ParameterSchema for the item type to enable recursion.
                # This is a simplified conversion for coercion purposes only.
                from autobyteus.utils.parameter_schema import ParameterSchema as TempSchema
                from autobyteus.utils.parameter_schema import ParameterDefinition as TempDef

                item_param_schema = TempSchema()
                props = item_schema_dict.get("properties", {})
                reqs = item_schema_dict.get("required", [])
                for prop_name, prop_details in props.items():
                    # This is a simplified conversion and might not capture all details,
                    # but it's sufficient for recursive coercion.
                    prop_type_str = prop_details.get("type", "string")
                    try:
                        prop_type = ParameterType(prop_type_str)
                    except ValueError:
                        prop_type = ParameterType.STRING
                    
                    item_param_schema.add_parameter(TempDef(
                        name=prop_name,
                        param_type=prop_type,
                        description=prop_details.get("description", ""),
                        required=prop_name in reqs,
                        array_item_schema=prop_details.get("items") # Pass down nested array schemas
                    ))
                
                return [self._coerce_object_recursively(item, item_param_schema) for item in value if isinstance(item, dict)]

            return value # Return list of primitives as is

        # 4. Coerce primitives if they are passed as strings
        if isinstance(value, str):
            try:
                if param_def.param_type == ParameterType.INTEGER:
                    return int(value)
                elif param_def.param_type == ParameterType.FLOAT:
                    return float(value)
                elif param_def.param_type == ParameterType.BOOLEAN:
                    lower_val = value.lower()
                    if lower_val in ["true", "1", "yes"]:
                        return True
                    elif lower_val in ["false", "0", "no"]:
                        return False
            except (ValueError, TypeError):
                logger.warning(f"Could not coerce argument '{param_def.name}' with value '{value}' to type {param_def.param_type}. "
                               f"Passing string value to tool.")
        
        return value

    def set_agent_id(self, agent_id: str):
        if not isinstance(agent_id, str) or not agent_id:
            logger.error(f"Attempted to set invalid agent_id: {agent_id} for tool {self.get_name()}")
            return
        self.agent_id = agent_id
        logger.debug(f"Agent ID '{agent_id}' set for tool instance '{self.__class__.get_name()}'")

    async def execute(self, context: 'AgentContext', **kwargs):
        tool_name = self.get_name()
        if self.agent_id is None:
            self.set_agent_id(context.agent_id)
        
        # Coerce types before validation and execution
        coerced_kwargs = self._coerce_argument_types(kwargs)
        
        arg_schema = self.get_argument_schema() 
        if arg_schema:
            is_valid, errors = arg_schema.validate_config(coerced_kwargs)
            if not is_valid:
                error_message = f"Invalid arguments for tool '{tool_name}': {'; '.join(errors)}"
                logger.error(error_message)
                raise ValueError(error_message)
        elif coerced_kwargs: 
            logger.warning(f"Tool '{tool_name}' does not define an argument schema but received arguments: {coerced_kwargs}. These will be passed to _execute.")

        logger.info(f"Executing tool '{tool_name}' for agent '{self.agent_id}' with args: {coerced_kwargs}")
        try:
            result = await self._execute(context=context, **coerced_kwargs) 
            logger.info(f"Tool '{tool_name}' execution completed successfully for agent '{self.agent_id}'.")
            return result
        except Exception as e:
            logger.error(f"Tool '{tool_name}' execution failed for agent '{self.agent_id}': {type(e).__name__} - {str(e)}", exc_info=True)
            raise

    @abstractmethod
    async def _execute(self, context: 'AgentContext', **kwargs) -> Any:
        raise NotImplementedError("Subclasses must implement the '_execute' method.")

    @classmethod
    def tool_usage(cls) -> str:
        logger.warning("BaseTool.tool_usage() is deprecated. Tool usage is now generated by formatters.")
        # To maintain some backward compatibility without errors, we can generate a basic XML representation.
        # This should ideally not be called by new code.
        from autobyteus.tools.usage.formatters.default_xml_schema_formatter import DefaultXmlSchemaFormatter
        return DefaultXmlSchemaFormatter().provide(cls)
