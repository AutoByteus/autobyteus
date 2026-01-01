# file: autobyteus/autobyteus/agent/streaming/__init__.py
"""
Components related to agent output streaming.

Main components:
- StreamingResponseHandler: High-level handler for LLM response parsing
- StreamingParser: Low-level character-by-character parser
- SegmentEvent: Structured events for UI streaming

Legacy components (for backward compatibility):
- StreamEvent, StreamEventType: Old event format
- AgentEventStream: Old stream consumer
"""
from .stream_events import StreamEventType, StreamEvent
from .agent_event_stream import AgentEventStream     
from .queue_streamer import stream_queue_items
from .streaming_response_handler import StreamingResponseHandler

# Re-export commonly used parser components
from .parser import (
    StreamingParser,
    SegmentEvent,
    SegmentType,
    SegmentEventType,
    ToolInvocationAdapter,
    ParserConfig,
    parse_complete_response,
    extract_segments,
)

__all__ = [
    # New streaming API
    "StreamingResponseHandler",
    "StreamingParser",
    "SegmentEvent",
    "SegmentType",
    "SegmentEventType",
    "ToolInvocationAdapter",
    "ParserConfig",
    "parse_complete_response",
    "extract_segments",
    
    # Legacy (backward compatible)
    "StreamEventType",
    "StreamEvent",
    "AgentEventStream",   
    "stream_queue_items", 
]
