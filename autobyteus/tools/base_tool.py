# File: autobyteus/tools/base_tool.py

import logging
from abc import ABC, abstractmethod
from autobyteus.events.event_emitter import EventEmitter
from autobyteus.events.event_types import EventType
from autobyteus.events.decorators import publish_event, event_listener

logger = logging.getLogger('autobyteus')

class BaseTool(EventEmitter, ABC):
    def __init__(self):
        super().__init__()

    async def execute(self, **kwargs):
        """Execute the tool's main functionality."""
        self.emit(EventType.TOOL_EXECUTION_STARTED)
        try:
            result = await self._execute(**kwargs)
            self.emit(EventType.TOOL_EXECUTION_COMPLETED, result)
            return result
        except Exception as e:
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

    @event_listener(EventType.TOOL_EXECUTION_STARTED)
    def on_execution_started(self, *args, **kwargs):
        logger.info(f"{self.__class__.__name__} execution started")

    @event_listener(EventType.TOOL_EXECUTION_COMPLETED)
    def on_execution_completed(self, result):
        logger.info(f"{self.__class__.__name__} execution completed with result: {result}")

    @event_listener(EventType.TOOL_EXECUTION_FAILED)
    def on_execution_failed(self, error):
        logger.error(f"{self.__class__.__name__} execution failed with error: {error}")