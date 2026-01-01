"""
JsonToolParsingState: Parses JSON tool call content.

This state handles parsing JSON-formatted tool calls from providers
like OpenAI that use {"name": "...", "arguments": {...}} format.
"""
import json
import re
from typing import TYPE_CHECKING, Optional, Dict, Any

from .base_state import BaseState
from ..events import SegmentType

if TYPE_CHECKING:
    from ..parser_context import ParserContext


class JsonToolParsingState(BaseState):
    """
    Parses JSON tool call content.
    
    Expected formats:
    - {"name": "tool_name", "arguments": {...}}
    - [{"name": "tool_name", "arguments": {...}}]
    
    Handles nested braces and proper JSON parsing.
    """
    
    def __init__(self, context: "ParserContext", signature_buffer: str):
        super().__init__(context)
        self._signature_buffer = signature_buffer
        self._content_buffer = ""
        self._brace_count = 0
        self._bracket_count = 0
        self._in_string = False
        self._escape_next = False
        self._segment_started = False
        self._is_array = signature_buffer.startswith('[')

    def run(self) -> None:
        """
        Parse JSON tool content, tracking nested braces.
        """
        from .text_state import TextState
        
        # Consume the signature buffer
        self.context.advance_by(len(self._signature_buffer))
        self._content_buffer = self._signature_buffer
        
        # Count initial braces/brackets
        for char in self._signature_buffer:
            self._update_brace_count(char)
        
        # Start segment - we'll extract name later when JSON is complete
        if not self._segment_started:
            self.context.emit_segment_start(SegmentType.TOOL_CALL)
            self._segment_started = True
        
        while self.context.has_more_chars():
            char = self.context.peek_char()
            self._content_buffer += char
            self.context.advance()
            
            self._update_brace_count(char)
            
            # Check if JSON is complete
            if self._is_json_complete():
                # Parse the complete JSON
                tool_info = self._parse_json_tool_call(self._content_buffer)
                
                if tool_info:
                    # Update metadata with parsed info
                    self.context.update_current_segment_metadata(
                        tool_name=tool_info.get("name", "unknown"),
                        arguments=tool_info.get("arguments", {})
                    )
                    
                    # Emit the raw JSON as content for display
                    self.context.emit_segment_content(self._content_buffer)
                else:
                    # Invalid JSON - emit as text instead
                    self.context.emit_segment_content(self._content_buffer)
                
                self.context.emit_segment_end()
                self.context.transition_to(TextState(self.context))
                return
        
        # Buffer exhausted but JSON not complete
        # Emit partial content for streaming display
        if self._content_buffer:
            self.context.emit_segment_content(self._content_buffer)
            self._content_buffer = ""

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

    def _parse_json_tool_call(self, json_str: str) -> Optional[Dict[str, Any]]:
        """
        Parse a JSON string into tool call info.
        
        Returns dict with 'name' and 'arguments', or None if invalid.
        """
        try:
            data = json.loads(json_str)
            
            # Handle array format
            if isinstance(data, list) and len(data) > 0:
                data = data[0]
            
            if isinstance(data, dict):
                # Extract tool name from various formats
                name = (
                    data.get("name") or 
                    data.get("tool") or 
                    data.get("function", {}).get("name") or
                    "unknown"
                )
                
                # Extract arguments from various formats
                arguments = (
                    data.get("arguments") or 
                    data.get("parameters") or
                    data.get("function", {}).get("arguments") or
                    {}
                )
                
                # Arguments might be a JSON string
                if isinstance(arguments, str):
                    try:
                        arguments = json.loads(arguments)
                    except json.JSONDecodeError:
                        pass
                
                return {"name": name, "arguments": arguments}
        except json.JSONDecodeError:
            pass
        
        return None

    def finalize(self) -> None:
        """
        Called when stream ends while parsing JSON.
        
        Emit any remaining content and close the segment.
        """
        from .text_state import TextState
        
        if self._segment_started:
            if self._content_buffer:
                self.context.emit_segment_content(self._content_buffer)
            self.context.emit_segment_end()
        else:
            if self._content_buffer:
                self.context.append_text_segment(self._content_buffer)
        
        self.context.transition_to(TextState(self.context))
