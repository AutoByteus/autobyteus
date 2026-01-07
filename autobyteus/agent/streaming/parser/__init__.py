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
from .xml_tool_parsing_state_registry import XmlToolParsingStateRegistry
from .states.xml_tool_parsing_state import XmlToolParsingState
from .states.xml_write_file_tool_parsing_state import XmlWriteFileToolParsingState
from .states.xml_patch_file_tool_parsing_state import XmlPatchFileToolParsingState

def register_xml_tool_parsing_state(tool_name: str, state_class):
    """
    Public API to register a custom parsing state for a specific tool.
    
    Args:
        tool_name: The name of the tool (e.g., 'patch_prompt').
        state_class: The parsing state class (must inherit from XmlToolParsingState or BaseState).
    """
    XmlToolParsingStateRegistry().register_tool_state(tool_name, state_class)

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
    
    # Public Registry API
    "register_xml_tool_parsing_state",
    "XmlToolParsingStateRegistry",
    
    # Base States for inheritance
    "XmlToolParsingState",
    "XmlWriteFileToolParsingState",
    "XmlPatchFileToolParsingState",
]
