"""
RunBashParsingState: Parses <run_bash>...</run_bash> blocks.

Simplified implementation that parses terminal commands.
"""
from typing import TYPE_CHECKING

from .delimited_content_state import DelimitedContentState
from ..events import SegmentType

if TYPE_CHECKING:
    from ..parser_context import ParserContext


class CustomXmlTagRunBashParsingState(DelimitedContentState):
    """
    Parses terminal command blocks.
    
    Supported format: <run_bash>command</run_bash>
    
    The state:
    1. Emits SEGMENT_START (no metadata)
    2. Streams command content as SEGMENT_CONTENT events
    3. Emits SEGMENT_END when </run_bash> is found
    """
    
    CLOSING_TAG = "</run_bash>"
    SEGMENT_TYPE = SegmentType.RUN_BASH
    
    def __init__(self, context: "ParserContext", opening_tag: str):
        """
        Initialize the run_bash parsing state.
        
        Args:
            context: The parser context.
            opening_tag: The opening tag (e.g., '<run_bash>').
        """
        super().__init__(context, opening_tag)
