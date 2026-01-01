"""
BashParsingState: Parses <bash>...</bash> blocks.

Simplified implementation that only supports the standard <bash>command</bash> format.
Removes support for description attributes or comment parsing.

DESIGN: Independent state with its own run() logic.
Buffer handling uses position tracking to avoid content loss around closing tags.
"""
from typing import TYPE_CHECKING

from .base_state import BaseState
from ..events import SegmentType

if TYPE_CHECKING:
    from ..parser_context import ParserContext


class BashParsingState(BaseState):
    """
    Parses bash command blocks.
    
    Supported format: <bash>command</bash>
    
    The state:
    1. Emits SEGMENT_START (no metadata)
    2. Streams command content as SEGMENT_CONTENT events
    3. Emits SEGMENT_END when </bash> is found
    """
    
    CLOSING_TAG = "</bash>"
    
    def __init__(self, context: "ParserContext", opening_tag: str):
        """
        Initialize the bash parsing state.
        
        Args:
            context: The parser context.
            opening_tag: The opening tag (e.g., '<bash>').
        """
        super().__init__(context)
        self._opening_tag = opening_tag
        self._content_buffer = ""      # Full content for parsing
        self._emitted_length = 0       # Track how much has been streamed
        self._segment_started = False
        
    def run(self) -> None:
        """
        Parse bash content from the stream.
        """
        from .text_state import TextState
        
        # Start the segment (first run only)
        if not self._segment_started:
            self.context.emit_segment_start(SegmentType.BASH)
            self._segment_started = True
        
        while self.context.has_more_chars():
            char = self.context.peek_char()
            self._content_buffer += char
            self.context.advance()
            
            # Check for closing tag (case-insensitive)
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
        
        # Buffer exhausted but bash not complete
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
        Called when stream ends while parsing bash.
        
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
