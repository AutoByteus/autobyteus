# File: autobyteus/tools/base_tool.py

import logging
from abc import ABC, abstractmethod
from typing import Optional, Any

from autobyteus.events.event_emitter import EventEmitter
from autobyteus.events.event_types import EventType

from .tool_meta import ToolMeta

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
        logger.debug(f"BaseTool instance initializing for potential class {self.__class__.__name__}")

    @classmethod
    def get_name(cls) -> str:
        """
        Return the name of the tool. Defaults to the class name.
        Can be overridden by child classes if a different registration name is needed.
        """
        return cls.__name__
    
    @classmethod
    def tool_usage_xml(cls) -> str:
        """
        Return the static usage description string for the tool in XML format.
        Must be implemented by subclasses.
        """
        pass

    def set_agent_id(self, agent_id: str):
        """Sets the ID of the agent using this tool instance."""
        self.agent_id = agent_id
        logger.debug(f"Agent ID '{agent_id}' set for tool instance '{self.__class__.get_name()}'")

    async def execute(self, **kwargs):
        """
        Execute the tool's main functionality by calling _execute.
        Argument validation must be handled within _execute.
        """
        tool_name = self.__class__.get_name()
        logger.info(f"Executing tool '{tool_name}' for agent '{self.agent_id}' with args: {kwargs}")
        try:
            result = await self._execute(**kwargs)
            logger.info(f"Tool '{tool_name}' execution completed successfully.")
            return result
        except Exception as e:
            logger.error(f"Tool '{tool_name}' execution failed: {str(e)}", exc_info=True)
            return f"Error executing tool '{tool_name}': {str(e)}"

    @abstractmethod
    async def _execute(self, **kwargs) -> Any:
        """
        Implement the actual execution logic in subclasses.
        MUST handle own argument validation.
        """
        pass

    @classmethod
    def tool_usage(cls) -> str:
        """
        Returns the tool's static XML usage description by calling the class method tool_usage_xml.
        This is a convenience class method.
        """
        return cls.tool_usage_xml()
