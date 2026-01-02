"""
BashParsingState: Parses <bash>...</bash> blocks.

Simplified implementation that only supports the standard <bash>command</bash> format.
Removes support for description attributes or comment parsing.
"""
from typing import TYPE_CHECKING

from .delimited_content_state import DelimitedContentState
from ..events import SegmentType

if TYPE_CHECKING:
    from ..parser_context import ParserContext


class BashParsingState(DelimitedContentState):
    """
    Parses bash command blocks.
    
    Supported format: <bash>command</bash>
    
    The state:
    1. Emits SEGMENT_START (no metadata)
    2. Streams command content as SEGMENT_CONTENT events
    3. Emits SEGMENT_END when </bash> is found
    """
    
    CLOSING_TAG = "</bash>"
    SEGMENT_TYPE = SegmentType.BASH
    
    def __init__(self, context: "ParserContext", opening_tag: str):
        """
        Initialize the bash parsing state.
        
        Args:
            context: The parser context.
            opening_tag: The opening tag (e.g., '<bash>').
        """
        super().__init__(context, opening_tag)
