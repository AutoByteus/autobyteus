"""
StreamingResponseHandler: Abstract Base Class for response handlers.
"""
from abc import ABC, abstractmethod
from typing import List, Optional, Callable
from autobyteus.agent.tool_invocation import ToolInvocation
from .parser.events import SegmentEvent

class StreamingResponseHandler(ABC):
    """
    Abstract base class for handling streaming LLM responses.
    """

    @abstractmethod
    def feed(self, chunk: str) -> List[SegmentEvent]:
        """
        Process a chunk of LLM response text.
        """
        pass

    @abstractmethod
    def finalize(self) -> List[SegmentEvent]:
        """
        Finalize parsing and emit any remaining segments.
        """
        pass

    @abstractmethod
    def get_all_invocations(self) -> List[ToolInvocation]:
        """
        Get all ToolInvocations created so far.
        """
        pass

    @abstractmethod
    def get_all_events(self) -> List[SegmentEvent]:
        """
        Get all SegmentEvents emitted so far.
        """
        pass
    
    @abstractmethod
    def reset(self) -> None:
        """
        Reset the handler for reuse.
        """
        pass
