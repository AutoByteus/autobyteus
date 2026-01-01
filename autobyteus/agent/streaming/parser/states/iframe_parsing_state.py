"""
IframeParsingState: Parses <!doctype html>...</html> blocks.

This state handles HTML content blocks that start with a DOCTYPE declaration.
It emits the content as an IFRAME segment.

DESIGN: Independent state with its own run() logic.
"""
from typing import TYPE_CHECKING

from .base_state import BaseState
from ..events import SegmentType

if TYPE_CHECKING:
    from ..parser_context import ParserContext


class IframeParsingState(BaseState):
    """
    Parses iframe/HTML content blocks.
    
    Expected format: <!doctype html>...content...</html>
    
    The state:
    1. Emits SEGMENT_START with type IFRAME
    2. Streams HTML content as SEGMENT_CONTENT events
    3. Emits SEGMENT_END when </html> is found
    """
    
    CLOSING_TAG = "</html>"
    
    def __init__(self, context: "ParserContext", opening_tag: str):
        """
        Initialize the iframe parsing state.
        
        Args:
            context: The parser context.
            opening_tag: The DOCTYPE declaration (e.g., '<!doctype html>').
        """
        super().__init__(context)
        self._opening_tag = opening_tag
        self._content_buffer = ""      # Full content for parsing
        self._emitted_length = 0       # Track how much has been streamed
        self._segment_started = False

    def run(self) -> None:
        """
        Parse iframe/HTML content from the stream.
        """
        from .text_state import TextState
        
        # Start the segment (first run only)
        if not self._segment_started:
            self.context.emit_segment_start(SegmentType.IFRAME)
            # Emit the opening tag as content
            self.context.emit_segment_content(self._opening_tag)
            self._segment_started = True
        
        while self.context.has_more_chars():
            char = self.context.peek_char()
            self._content_buffer += char
            self.context.advance()
            
            # Check for closing tag (case-insensitive)
            if self._content_buffer.lower().endswith(self.CLOSING_TAG):
                # Emit all content including closing tag
                unemitted = self._content_buffer[self._emitted_length:]
                if unemitted:
                    self.context.emit_segment_content(unemitted)
                
                self.context.emit_segment_end()
                self.context.transition_to(TextState(self.context))
                return
        
        # Buffer exhausted but HTML not complete
        # Stream content safely (hold back potential closing tag chars)
        self._stream_safe_content()

    def _stream_safe_content(self) -> None:
        """
        Stream new content while holding back potential closing tag characters.
        """
        safe_length = len(self._content_buffer) - (len(self.CLOSING_TAG) - 1)
        
        if safe_length > self._emitted_length:
            unemitted = self._content_buffer[self._emitted_length:safe_length]
            if unemitted:
                self.context.emit_segment_content(unemitted)
                self._emitted_length = safe_length

    def finalize(self) -> None:
        """
        Called when stream ends while parsing HTML.
        
        Emit any remaining content and close the segment.
        """
        from .text_state import TextState
        
        if self._segment_started:
            # Emit any remaining content
            unemitted = self._content_buffer[self._emitted_length:]
            if unemitted:
                self.context.emit_segment_content(unemitted)
            self.context.emit_segment_end()
        else:
            # Never started - treat as text
            self.context.append_text_segment(self._opening_tag + self._content_buffer)
        
        self.context.transition_to(TextState(self.context))
