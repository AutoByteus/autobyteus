# File: autobyteus/tools/base_tool.py

import logging
from abc import ABC, abstractmethod
from typing import Optional, Any, TYPE_CHECKING, List as TypingList, Dict
import xml.sax.saxutils

from autobyteus.events.event_emitter import EventEmitter
from autobyteus.events.event_types import EventType

from .tool_meta import ToolMeta
if TYPE_CHECKING:
    from autobyteus.agent.context import AgentContext
    from autobyteus.tools.parameter_schema import ParameterSchema
    from autobyteus.tools.tool_config import ToolConfig

logger = logging.getLogger('autobyteus')

class BaseTool(ABC, EventEmitter, metaclass=ToolMeta):
    """
    Abstract base class for all tools, with auto-registration via ToolMeta.
    """
    def __init__(self, config: Optional['ToolConfig'] = None):
        super().__init__()
        self.agent_id: Optional[str] = None
        # The config is stored primarily for potential use by subclasses or future base features.
        self._config = config
        logger.debug(f"BaseTool instance initializing for potential class {self.__class__.__name__}")

    @classmethod
    def get_name(cls) -> str:
        """Returns the registered name of the tool."""
        return cls.__name__
    
    @classmethod
    @abstractmethod
    def get_description(cls) -> str:
        """Returns the description of the tool."""
        raise NotImplementedError("Subclasses must implement get_description().")

    @classmethod
    @abstractmethod
    def get_argument_schema(cls) -> Optional['ParameterSchema']: 
        """
        Return a ParameterSchema defining the arguments this tool accepts for execution.
        Return None if the tool accepts no arguments.
        """
        raise NotImplementedError("Subclasses must implement get_argument_schema().")

    @classmethod
    def get_config_schema(cls) -> Optional['ParameterSchema']: 
        """
        Return the ParameterSchema for tool *instantiation* parameters.
        This is optional. By default, tools have no instantiation config.
        """
        return None

    @classmethod
    def tool_usage_xml(cls) -> str:
        """Generates the XML usage string based on the tool's class schema."""
        arg_schema = cls.get_argument_schema()
        tool_name = cls.get_name()
        description = cls.get_description()
        
        escaped_description = xml.sax.saxutils.escape(description) if description else ""
        command_tag = f'<command name="{tool_name}" description="{escaped_description}">'
        
        xml_parts = [command_tag]
        
        if arg_schema and arg_schema.parameters:
            for param in arg_schema.parameters: 
                arg_tag = f"    <arg name=\"{param.name}\""
                arg_tag += f" type=\"{param.param_type.value}\""
                if param.description:
                    escaped_param_desc = xml.sax.saxutils.escape(param.description)
                    arg_tag += f" description=\"{escaped_param_desc}\""
                arg_tag += f" required=\"{'true' if param.required else 'false'}\""

                if param.default_value is not None:
                    arg_tag += f" default=\"{str(param.default_value)}\""
                if param.enum_values:
                    arg_tag += f" enum_values=\"{','.join(param.enum_values)}\""
                
                arg_tag += " />"
                xml_parts.append(arg_tag)
        else:
            xml_parts.append("    <!-- This tool takes no arguments -->")
            
        xml_parts.append("</command>")
        
        return "\n".join(xml_parts)

    @classmethod
    def tool_usage_json(cls) -> Dict[str, Any]:
        """Generates the JSON usage dictionary based on the tool's class schema."""
        name = cls.get_name()
        description = cls.get_description()
        arg_schema = cls.get_argument_schema() 

        input_schema_dict = {}
        if arg_schema:
            input_schema_dict = arg_schema.to_json_schema_dict()
        else: 
            input_schema_dict = {
                "type": "object",
                "properties": {},
                "required": []
            }
            
        return {
            "name": name,
            "description": description,
            "inputSchema": input_schema_dict,
        }

    def set_agent_id(self, agent_id: str):
        if not isinstance(agent_id, str) or not agent_id:
            logger.error(f"Attempted to set invalid agent_id: {agent_id} for tool {self.get_name()}")
            return
        self.agent_id = agent_id
        logger.debug(f"Agent ID '{agent_id}' set for tool instance '{self.__class__.get_name()}'")

    async def execute(self, context: 'AgentContext', **kwargs):
        # In this context, self.get_name() will call the instance-specific method if it exists.
        tool_name = self.get_name()
        if self.agent_id is None:
            self.set_agent_id(context.agent_id)
        elif self.agent_id != context.agent_id:
            logger.warning(
                f"Tool '{tool_name}' current agent_id '{self.agent_id}' differs from "
                f"calling context's agent_id '{context.agent_id}'. Updating tool's agent_id."
            )
            self.set_agent_id(context.agent_id)
        
        arg_schema = self.get_argument_schema() 
        if arg_schema:
            is_valid, errors = arg_schema.validate_config(kwargs)
            if not is_valid:
                error_message = f"Invalid arguments for tool '{tool_name}': {'; '.join(errors)}"
                logger.error(error_message)
                raise ValueError(error_message)
        elif kwargs: 
            logger.warning(f"Tool '{tool_name}' does not define an argument schema but received arguments: {kwargs}. These will be passed to _execute.")

        logger.info(f"Executing tool '{tool_name}' for agent '{self.agent_id}' with args: {kwargs}")
        try:
            result = await self._execute(context=context, **kwargs) 
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
        logger.warning("BaseTool.tool_usage() is deprecated. Use tool_usage_xml() or tool_usage_json().")
        return cls.tool_usage_xml()
