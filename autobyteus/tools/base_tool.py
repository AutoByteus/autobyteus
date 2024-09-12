# File: autobyteus/tools/base_tool.py

import logging
from abc import ABC, abstractmethod
from typing import Optional
from autobyteus.events.event_emitter import EventEmitter
from autobyteus.events.event_types import EventType

logger = logging.getLogger('autobyteus')

class BaseTool(EventEmitter, ABC):
    def __init__(self):
        super().__init__()
        self.agent_id: Optional[str] = None

    def get_name(self) -> str:
        """Return the name of the tool. Can be overridden by child classes."""
        return self.__class__.__name__
    
    def set_agent_id(self, agent_id: str):
        self.agent_id = agent_id
        
    async def execute(self, **kwargs):
        """Execute the tool's main functionality."""
        tool_name = self.__class__.__name__
        logger.info(f"{tool_name} execution started")
        try:
            result = await self._execute(**kwargs)
            logger.info(f"{tool_name} execution completed")
            return result
        except Exception as e:
            logger.error(f"{tool_name} execution failed: {str(e)}")
            self.emit(EventType.TOOL_EXECUTION_FAILED, str(e))
            raise

    @abstractmethod
    async def _execute(self, **kwargs):
        """Implement the actual execution logic in subclasses."""
        pass

    @abstractmethod
    def tool_usage(self):
        """Return a string describing the usage of the tool."""
        pass

    @abstractmethod
    def tool_usage_xml(self):
        """Return a string describing the usage of the tool in XML format."""
        pass