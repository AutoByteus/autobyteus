# Parser package
"""
Streaming Parser: Character-by-character LLM response parser.

Main components:
- StreamingParser: Main entry point for parsing
- StreamingResponseHandler: High-level handler with callbacks
- ToolInvocationAdapter: Converts tool segments to ToolInvocations
- PartEvent: Structured events emitted during parsing
"""
from .streaming_parser import StreamingParser, parse_complete_response, extract_segments
from .events import (
    PartEvent,
    PartStartEvent,
    PartDeltaEvent,
    PartEndEvent,
    MessagePart,
    TextPart,
    ToolCallPart,
    ReasoningPart,
)
from .invocation_adapter import ToolInvocationAdapter
from .parser_context import ParserConfig

__all__ = [
    # Main classes
    "StreamingParser",
    "ToolInvocationAdapter",
    "ParserConfig",
    
    # Event types
    "PartEvent",
    "PartStartEvent",
    "PartDeltaEvent",
    "PartEndEvent",
    
    # Message parts
    "MessagePart",
    "TextPart",
    "ToolCallPart",
    "ReasoningPart",
    
    # Convenience functions
    "parse_complete_response",
    "extract_segments",
]
