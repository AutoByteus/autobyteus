# file: autobyteus/autobyteus/tools/base_tool.py
from abc import ABC, abstractmethod

from autobyteus.events.event_emitter import EventEmitter

class BaseTool(EventEmitter, ABC):
    def __init__(self):
        super().__init__()
    """
    An abstract base class that requires the implementation of an execute method and a description method.
    This is the core method all tools should provide.
    """
    @abstractmethod
    def execute(self, **kwargs):
        """Execute the tool's main functionality.

        Args:
            **kwargs: Keyword arguments that can be used to customize the tool's execution.
        """
        pass

    @abstractmethod
    def tool_usage(self):
        """
        Return a string describing the usage of the tool.
        """
        pass

    @abstractmethod
    def tool_usage_xml(self):
        """
        Return a string describing the usage of the tool in XML format.
        """
        pass
    