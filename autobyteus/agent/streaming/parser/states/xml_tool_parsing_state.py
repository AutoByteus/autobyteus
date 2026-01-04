"""
XmlToolParsingState: Streams <tool name="...">...</tool> blocks.

This state handles tool call boundaries and content streaming. Tool arguments
are parsed later by the ToolInvocationAdapter.
"""
import re
from typing import TYPE_CHECKING, Optional

from .delimited_content_state import DelimitedContentState
from ..events import SegmentType

if TYPE_CHECKING:
    from ..parser_context import ParserContext


class XmlToolParsingState(DelimitedContentState):
    """
    Streams tool call blocks.
    
    Expected format: <tool name="..."><arg>value</arg></tool>
    
    Supports two argument formats:
    1. Wrapped: <arguments><arg1>value1</arg1></arguments>
    2. Direct: <arg1>value1</arg1><arg2>value2</arg2>
    
    The state:
    1. Extracts tool name from the opening tag
    2. Emits SEGMENT_START with tool metadata
    3. Streams raw content for real-time display
    4. Emits SEGMENT_END when </tool> is found
    """
    
    # Pattern to extract tool name
    NAME_PATTERN = re.compile(r'name\s*=\s*["\']([^"\']+)["\']', re.IGNORECASE)
    CLOSING_TAG = "</tool>"
    SEGMENT_TYPE = SegmentType.TOOL_CALL
    def __init__(self, context: "ParserContext", opening_tag: str):
        """
        Initialize the tool parsing state.
        
        Args:
            context: The parser context.
            opening_tag: The complete opening tag (e.g., '<tool name="read_file">').
        """
        super().__init__(context, opening_tag)
        self._tool_name: Optional[str] = None
        
        # Extract tool name from opening tag
        match = self.NAME_PATTERN.search(opening_tag)
        if match:
            self._tool_name = match.group(1)

    def _can_start_segment(self) -> bool:
        return self._tool_name is not None

    def _get_start_metadata(self) -> dict:
        return {"tool_name": self._tool_name} if self._tool_name else {}

    def _on_segment_complete(self) -> None:
        return None

    # finalize inherited from DelimitedContentState
