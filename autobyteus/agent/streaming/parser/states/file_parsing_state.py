"""
FileParsingState: Parses <file path="...">...</file> blocks.

This state handles the extraction of file path from the tag attributes
and streams the file content until the closing </file> tag is found.

DESIGN: Independent state with its own run() logic for maximum flexibility.
Buffer handling uses position tracking to avoid content loss around closing tags.
"""
import re
from typing import TYPE_CHECKING, Optional

from .base_state import BaseState
from ..events import SegmentType

if TYPE_CHECKING:
    from ..parser_context import ParserContext


class FileParsingState(BaseState):
    """
    Parses file content blocks.
    
    Expected format: <file path="...">content</file>
    
    The state:
    1. Extracts the path attribute from the opening tag
    2. Emits SEGMENT_START with path metadata
    3. Streams content characters as SEGMENT_CONTENT events
    4. Emits SEGMENT_END when </file> is found
    """
    
    # Pattern to extract path from <file path="..."> or <file path='...'>
    PATH_PATTERN = re.compile(r'path\s*=\s*["\']([^"\']+)["\']', re.IGNORECASE)
    CLOSING_TAG = "</file>"
    
    def __init__(self, context: "ParserContext", opening_tag: str):
        """
        Initialize the file parsing state.
        
        Args:
            context: The parser context.
            opening_tag: The complete opening tag (e.g., '<file path="/a.py">').
        """
        super().__init__(context)
        self._opening_tag = opening_tag
        self._content_buffer = ""      # Full content for parsing
        self._emitted_length = 0       # Track how much has been streamed
        self._file_path: Optional[str] = None
        self._segment_started = False
        
        # Extract file path from opening tag
        match = self.PATH_PATTERN.search(opening_tag)
        if match:
            self._file_path = match.group(1)

    def run(self) -> None:
        """
        Parse file content from the stream.
        """
        from .text_state import TextState
        
        # Start the segment (first run only)
        if not self._segment_started:
            if self._file_path:
                self.context.emit_segment_start(
                    SegmentType.FILE,
                    path=self._file_path
                )
                self._segment_started = True
            else:
                # No valid path - treat as text
                self.context.append_text_segment(self._opening_tag)
                self.context.transition_to(TextState(self.context))
                return
        
        while self.context.has_more_chars():
            char = self.context.peek_char()
            self._content_buffer += char
            self.context.advance()
            
            # Check for closing tag
            if self._content_buffer.lower().endswith(self.CLOSING_TAG):
                # Remove closing tag from content
                content = self._content_buffer[:-len(self.CLOSING_TAG)]
                
                # Emit any remaining content not yet streamed
                unemitted = content[self._emitted_length:]
                if unemitted:
                    self.context.emit_segment_content(unemitted)
                
                self.context.emit_segment_end()
                self.context.transition_to(TextState(self.context))
                return
        
        # Buffer exhausted but file not complete
        # Stream content safely (hold back potential closing tag chars)
        self._stream_safe_content()

    def _stream_safe_content(self) -> None:
        """
        Stream new content while holding back potential closing tag characters.
        
        This prevents emitting partial closing tags like "</fi" before "</file>".
        """
        safe_length = len(self._content_buffer) - (len(self.CLOSING_TAG) - 1)
        
        if safe_length > self._emitted_length:
            unemitted = self._content_buffer[self._emitted_length:safe_length]
            if unemitted:
                self.context.emit_segment_content(unemitted)
                self._emitted_length = safe_length

    def finalize(self) -> None:
        """
        Called when stream ends while parsing a file.
        
        Emit any remaining content and close the segment.
        """
        from .text_state import TextState
        
        if not self._segment_started:
            # Never started - emit opening tag as text
            self.context.append_text_segment(self._opening_tag)
        else:
            # Emit any remaining content
            unemitted = self._content_buffer[self._emitted_length:]
            if unemitted:
                self.context.emit_segment_content(unemitted)
            
            # Close the segment
            self.context.emit_segment_end()
        
        self.context.transition_to(TextState(self.context))
