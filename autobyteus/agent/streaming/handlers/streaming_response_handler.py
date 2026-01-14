"""
StreamingResponseHandler: Abstract Base Class for response handlers.
"""
from abc import ABC, abstractmethod
from typing import List, Optional, Callable, Union
from autobyteus.agent.tool_invocation import ToolInvocation
from autobyteus.llm.utils.response_types import ChunkResponse
from ..segments.segment_events import SegmentEvent

class StreamingResponseHandler(ABC):
    """
    Abstract base class for handling streaming LLM responses.
    
    Handlers receive the full ChunkResponse object and decide which fields to use:
    - Text parsers use chunk.content
    - API tool call handlers use chunk.tool_calls
    """

    @abstractmethod
    def feed(self, chunk: ChunkResponse) -> List[SegmentEvent]:
        """
        Process a chunk of LLM response.
        
        Args:
            chunk: The full ChunkResponse containing text, tool calls, etc.
            
        Returns:
            List of SegmentEvents emitted while processing this chunk.
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
