"""
IframeParsingState: Parses <!doctype html>...</html> blocks.

This state handles HTML content blocks that start with a DOCTYPE declaration.
It emits the content as an IFRAME segment.

DESIGN: Independent state with its own run() logic.
"""
from typing import TYPE_CHECKING

from .delimited_content_state import DelimitedContentState
from ..events import SegmentType

if TYPE_CHECKING:
    from ..parser_context import ParserContext


class IframeParsingState(DelimitedContentState):
    """
    Parses iframe/HTML content blocks.
    
    Expected format: <!doctype html>...content...</html>
    
    The state:
    1. Emits SEGMENT_START with type IFRAME
    2. Streams HTML content as SEGMENT_CONTENT events
    3. Emits SEGMENT_END when </html> is found
    """
    
    CLOSING_TAG = "</html>"
    SEGMENT_TYPE = SegmentType.IFRAME
    
    def __init__(self, context: "ParserContext", opening_tag: str):
        """
        Initialize the iframe parsing state.
        
        Args:
            context: The parser context.
            opening_tag: The DOCTYPE declaration (e.g., '<!doctype html>').
        """
        super().__init__(context, opening_tag)

    def _opening_content(self) -> str:
        return self._opening_tag

    def _should_emit_closing_tag(self) -> bool:
        return True
