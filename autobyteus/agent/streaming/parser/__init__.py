# Parser package
"""
Streaming Parser: Character-by-character LLM response parser.

Main components:
- StreamingParser: Main entry point for parsing
- StreamingResponseHandler: High-level handler with callbacks
- ToolInvocationAdapter: Converts tool segments to ToolInvocations
- SegmentEvent: Structured events emitted during parsing
"""
from .streaming_parser import StreamingParser, parse_complete_response, extract_segments
from .parser_factory import (
    create_streaming_parser,
    resolve_parser_name,
    StreamingParserProtocol,
)
from .events import SegmentEvent, SegmentType, SegmentEventType
from .invocation_adapter import ToolInvocationAdapter
from .parser_context import ParserConfig

__all__ = [
    # Main classes
    "StreamingParser",
    "ToolInvocationAdapter",
    "ParserConfig",
    "StreamingParserProtocol",
    "create_streaming_parser",
    "resolve_parser_name",
    
    # Event types
    "SegmentEvent",
    "SegmentType",
    "SegmentEventType",
    
    # Convenience functions
    "parse_complete_response",
    "extract_segments",
]
