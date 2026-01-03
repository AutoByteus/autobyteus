"""
WriteFileParsingState: Parses <write_file path="...">...</write_file> blocks.

This state handles the extraction of file path from the tag attributes
and streams the file content until the closing </write_file> tag is found.
"""
import re
from typing import TYPE_CHECKING, Optional

from .delimited_content_state import DelimitedContentState
from ..events import SegmentType

if TYPE_CHECKING:
    from ..parser_context import ParserContext


class WriteFileParsingState(DelimitedContentState):
    """
    Parses write_file content blocks.
    
    Expected format: <write_file path="...">content</write_file>
    
    The state:
    1. Extracts the path attribute from the opening tag
    2. Emits SEGMENT_START with path metadata
    3. Streams content characters as SEGMENT_CONTENT events
    4. Emits SEGMENT_END when </write_file> is found
    """
    
    # Pattern to extract path from <write_file path="..."> or <write_file path='...'>
    PATH_PATTERN = re.compile(r'path\s*=\s*["\']([^"\']+)["\']', re.IGNORECASE)
    CLOSING_TAG = "</write_file>"
    SEGMENT_TYPE = SegmentType.WRITE_FILE
    
    def __init__(self, context: "ParserContext", opening_tag: str):
        """
        Initialize the write_file parsing state.
        
        Args:
            context: The parser context.
            opening_tag: The complete opening tag (e.g., '<write_file path="/a.py">').
        """
        super().__init__(context, opening_tag)
        self._file_path: Optional[str] = None
        
        # Extract file path from opening tag
        match = self.PATH_PATTERN.search(opening_tag)
        if match:
            self._file_path = match.group(1)

    def _can_start_segment(self) -> bool:
        return self._file_path is not None

    def _get_start_metadata(self) -> dict:
        return {"path": self._file_path} if self._file_path else {}
