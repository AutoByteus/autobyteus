"""
JsonToolParsingState: Streams JSON tool call content.

This state identifies JSON tool-call boundaries and streams raw JSON content.
Tool arguments are parsed later by the ToolInvocationAdapter.
"""
from typing import TYPE_CHECKING, List

from .base_state import BaseState
from ..events import SegmentType

if TYPE_CHECKING:
    from ..parser_context import ParserContext


class JsonToolParsingState(BaseState):
    """
    Streams JSON tool call content.
    
    Expected formats:
    - {"name": "tool_name", "arguments": {...}}
    - [{"name": "tool_name", "arguments": {...}}]
    
    Handles nested braces and proper JSON boundary detection.
    """
    
    def __init__(
        self,
        context: "ParserContext",
        signature_buffer: str,
        signature_consumed: bool = False,
    ):
        super().__init__(context)
        self._signature_buffer = signature_buffer
        self._signature_consumed = signature_consumed
        self._brace_count = 0
        self._bracket_count = 0
        self._in_string = False
        self._escape_next = False
        self._segment_started = False
        self._initialized = False
        self._is_array = signature_buffer.startswith('[')

    def run(self) -> None:
        """
        Parse JSON tool content, tracking nested braces.
        """
        from .text_state import TextState
        
        if not self._segment_started:
            self.context.emit_segment_start(SegmentType.TOOL_CALL)
            self._segment_started = True

        consumed: List[str] = []

        if not self._initialized:
            if self._signature_consumed:
                consumed.append(self._signature_buffer)
                for char in self._signature_buffer:
                    self._update_brace_count(char)
            else:
                signature = self.context.consume(len(self._signature_buffer))
                if signature:
                    consumed.append(signature)
                    for char in signature:
                        self._update_brace_count(char)
            self._initialized = True

        while self.context.has_more_chars():
            char = self.context.peek_char()
            self.context.advance()
            consumed.append(char)
            self._update_brace_count(char)

            if self._is_json_complete():
                if consumed:
                    self.context.emit_segment_content("".join(consumed))

                self.context.emit_segment_end()
                self.context.transition_to(TextState(self.context))
                return

        if consumed:
            self.context.emit_segment_content("".join(consumed))

    def _update_brace_count(self, char: str) -> None:
        """Update brace/bracket count, handling strings."""
        if self._escape_next:
            self._escape_next = False
            return
        
        if char == '\\' and self._in_string:
            self._escape_next = True
            return
        
        if char == '"' and not self._escape_next:
            self._in_string = not self._in_string
            return
        
        if self._in_string:
            return
        
        if char == '{':
            self._brace_count += 1
        elif char == '}':
            self._brace_count -= 1
        elif char == '[':
            self._bracket_count += 1
        elif char == ']':
            self._bracket_count -= 1

    def _is_json_complete(self) -> bool:
        """Check if we have a complete JSON structure."""
        if self._in_string:
            return False
        
        if self._is_array:
            return self._bracket_count == 0 and self._brace_count == 0
        else:
            return self._brace_count == 0

    def finalize(self) -> None:
        """
        Called when stream ends while parsing JSON.
        
        Emit any remaining content and close the segment.
        """
        from .text_state import TextState
        
        if self.context.has_more_chars():
            remaining = self.context.consume_remaining()
            if remaining:
                self.context.emit_segment_content(remaining)

        if self._segment_started:
            self.context.emit_segment_end()
        self.context.transition_to(TextState(self.context))
