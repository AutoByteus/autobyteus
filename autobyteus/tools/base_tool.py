# File: autobyteus/tools/base_tool.py

import logging
from abc import ABC, abstractmethod
from typing import Optional, Any, TYPE_CHECKING

from autobyteus.events.event_emitter import EventEmitter
from autobyteus.events.event_types import EventType

from .tool_meta import ToolMeta

if TYPE_CHECKING:
    from autobyteus.agent.context import AgentContext

logger = logging.getLogger('autobyteus')

class BaseTool(ABC, EventEmitter, metaclass=ToolMeta):
    """
    Abstract base class for all tools, with auto-registration via ToolMeta.

    Subclasses inherit a default `get_name` (the class name) and MUST implement
    the abstract class method `tool_usage_xml`, and the abstract instance
    method `_execute`.
    """
    def __init__(self):
        super().__init__()
        self.agent_id: Optional[str] = None
        # current_agent_context is removed as context is passed directly to execute/_execute
        logger.debug(f"BaseTool instance initializing for potential class {self.__class__.__name__}")

    @classmethod
    def get_name(cls) -> str:
        """
        Return the name of the tool. Defaults to the class name.
        Can be overridden by child classes if a different registration name is needed.
        """
        return cls.__name__
    
    @classmethod
    @abstractmethod # Ensure this is decorated as abstractmethod if tool_usage_xml must be implemented
    def tool_usage_xml(cls) -> str:
        """
        Return the static usage description string for the tool in XML format.
        Must be implemented by subclasses.
        """
        raise NotImplementedError("Subclasses must implement tool_usage_xml().")


    def set_agent_id(self, agent_id: str):
        """Sets the ID of the agent using this tool instance."""
        if not isinstance(agent_id, str) or not agent_id:
            logger.error(f"Attempted to set invalid agent_id: {agent_id} for tool {self.__class__.get_name()}")
            return
        self.agent_id = agent_id
        logger.debug(f"Agent ID '{agent_id}' set for tool instance '{self.__class__.get_name()}'")

    async def execute(self, context: 'AgentContext', **kwargs):
        """
        Execute the tool's main functionality by calling _execute.
        The AgentContext is passed to this method and then to _execute.
        Sets/updates the tool's agent_id from the context.

        Args:
            context: The AgentContext of the calling agent.
            **kwargs: Arguments for the specific tool's _execute method.
        """
        tool_name = self.__class__.get_name()
        # Set or verify agent_id
        if self.agent_id is None:
            self.set_agent_id(context.agent_id)
        elif self.agent_id != context.agent_id:
            logger.warning(
                f"Tool '{tool_name}' current agent_id '{self.agent_id}' differs from "
                f"calling context's agent_id '{context.agent_id}'. Updating tool's agent_id."
            )
            self.set_agent_id(context.agent_id)
        
        logger.info(f"Executing tool '{tool_name}' for agent '{self.agent_id}' with args: {kwargs}")
        try:
            result = await self._execute(context=context, **kwargs) # Pass context to _execute
            logger.info(f"Tool '{tool_name}' execution completed successfully for agent '{self.agent_id}'.")
            return result
        except Exception as e:
            logger.error(f"Tool '{tool_name}' execution failed for agent '{self.agent_id}': {type(e).__name__} - {str(e)}", exc_info=True)
            return f"Error executing tool '{tool_name}': {type(e).__name__} - {str(e)}"


    @abstractmethod
    async def _execute(self, context: 'AgentContext', **kwargs) -> Any:
        """
        Implement the actual execution logic in subclasses.
        MUST handle own argument validation.

        Args:
            context: The AgentContext of the calling agent.
            **kwargs: Tool-specific arguments.
        """
        raise NotImplementedError("Subclasses must implement the '_execute' method.")

    @classmethod
    def tool_usage(cls) -> str:
        """
        Returns the tool's static XML usage description by calling the class method tool_usage_xml.
        This is a convenience class method.
        """
        return cls.tool_usage_xml()
