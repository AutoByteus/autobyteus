"""
PassThroughStreamingResponseHandler: Implementation of StreamingResponseHandler that bypasses parsing.
"""
import uuid
import logging
from typing import Optional, List, Callable

from .streaming_response_handler import StreamingResponseHandler
from ..segments.segment_events import SegmentEvent, SegmentType, SegmentEventType
from autobyteus.agent.tool_invocation import ToolInvocation
from autobyteus.llm.utils.response_types import ChunkResponse

logger = logging.getLogger(__name__)


class PassThroughStreamingResponseHandler(StreamingResponseHandler):
    """
    Handler that passes raw text chunks directly as segment events without parsing.
    Used when an agent has no tools configured.
    """
    
    def __init__(
        self,
        on_segment_event: Optional[Callable[[SegmentEvent], None]] = None,
        on_tool_invocation: Optional[Callable[[ToolInvocation], None]] = None,
        segment_id_prefix: Optional[str] = None,
    ):
        """
        Initialize the pass-through handler.
        
        Args:
            on_segment_event: Callback for UI streaming.
            on_tool_invocation: Callback for tools (unused here, kept for compatibility).
            segment_id_prefix: Prefix for the single text segment ID.
        """
        self._on_segment_event = on_segment_event
        self._segment_id_prefix = segment_id_prefix or f"pt_{uuid.uuid4().hex}:"
        self._segment_id = f"{self._segment_id_prefix}text_0"
        self._is_active = False
        self._is_finalized = False
        self._all_events: List[SegmentEvent] = []

    def feed(self, chunk: ChunkResponse) -> List[SegmentEvent]:
        if self._is_finalized:
            raise RuntimeError("Handler has been finalized, cannot feed more chunks.")
        
        # Extract text content from ChunkResponse
        text_content = chunk.content if isinstance(chunk, ChunkResponse) else chunk
        if not text_content:
            return []
        
        events = []
        
        # Start segment if not active
        if not self._is_active:
            self._is_active = True
            start_event = SegmentEvent.start(
                segment_id=self._segment_id,
                segment_type=SegmentType.TEXT
            )
            events.append(start_event)
        
        # Content event
        content_event = SegmentEvent.content(
            segment_id=self._segment_id,
            delta=text_content
        )
        events.append(content_event)
        
        self._process_events(events)
        return events

    def finalize(self) -> List[SegmentEvent]:
        if self._is_finalized:
            return []
        
        self._is_finalized = True
        events = []
        
        if self._is_active:
            end_event = SegmentEvent.end(segment_id=self._segment_id)
            events.append(end_event)
            self._is_active = False
            
        self._process_events(events)
        return events

    def _process_events(self, events: List[SegmentEvent]) -> None:
        for event in events:
            self._all_events.append(event)
            if self._on_segment_event:
                try:
                    self._on_segment_event(event)
                except Exception as e:
                    logger.error(f"Error in on_segment_event callback: {e}")

    def get_all_events(self) -> List[SegmentEvent]:
        return self._all_events.copy()

    def get_all_invocations(self) -> List[ToolInvocation]:
        return []

    def reset(self) -> None:
        self._segment_id = f"{self._segment_id_prefix}text_{uuid.uuid4().hex}"
        self._is_active = False
        self._is_finalized = False
        self._all_events.clear()
