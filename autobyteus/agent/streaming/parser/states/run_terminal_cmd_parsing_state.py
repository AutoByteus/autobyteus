"""
RunTerminalCmdParsingState: Parses <run_terminal_cmd>...</run_terminal_cmd> blocks.

Simplified implementation that parses terminal commands.
"""
from typing import TYPE_CHECKING

from .delimited_content_state import DelimitedContentState
from ..events import SegmentType

if TYPE_CHECKING:
    from ..parser_context import ParserContext


class RunTerminalCmdParsingState(DelimitedContentState):
    """
    Parses terminal command blocks.
    
    Supported format: <run_terminal_cmd>command</run_terminal_cmd>
    
    The state:
    1. Emits SEGMENT_START (no metadata)
    2. Streams command content as SEGMENT_CONTENT events
    3. Emits SEGMENT_END when </run_terminal_cmd> is found
    """
    
    CLOSING_TAG = "</run_terminal_cmd>"
    SEGMENT_TYPE = SegmentType.RUN_TERMINAL_CMD
    
    def __init__(self, context: "ParserContext", opening_tag: str):
        """
        Initialize the run_terminal_cmd parsing state.
        
        Args:
            context: The parser context.
            opening_tag: The opening tag (e.g., '<run_terminal_cmd>').
        """
        super().__init__(context, opening_tag)
