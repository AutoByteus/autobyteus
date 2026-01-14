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
from .events.stream_events import StreamEventType, StreamEvent
from .streams.agent_event_stream import AgentEventStream
from .utils.queue_streamer import stream_queue_items
from .handlers.streaming_response_handler import StreamingResponseHandler
from .handlers.streaming_handler_factory import StreamingResponseHandlerFactory
from .handlers.parsing_streaming_response_handler import ParsingStreamingResponseHandler
from .handlers.pass_through_streaming_response_handler import PassThroughStreamingResponseHandler
from .handlers.api_tool_call_streaming_response_handler import ApiToolCallStreamingResponseHandler

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
    StreamingParserProtocol,
    create_streaming_parser,
    resolve_parser_name,
)

__all__ = [
    # New streaming API
    "StreamingResponseHandler",
    "StreamingResponseHandlerFactory",
    "ParsingStreamingResponseHandler",
    "PassThroughStreamingResponseHandler",
    "ApiToolCallStreamingResponseHandler",
    "StreamingParser",
    "SegmentEvent",
    "SegmentType",
    "SegmentEventType",
    "ToolInvocationAdapter",
    "ParserConfig",
    "parse_complete_response",
    "extract_segments",
    "StreamingParserProtocol",
    "create_streaming_parser",
    "resolve_parser_name",
    
    # Legacy (backward compatible)
    "StreamEventType",
    "StreamEvent",
    "AgentEventStream",   
    "stream_queue_items", 
]
