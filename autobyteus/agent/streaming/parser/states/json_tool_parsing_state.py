"""
JsonToolParsingState: Parses JSON tool call content.

This state handles parsing JSON-formatted tool calls from providers
like OpenAI that use {"name": "...", "arguments": {...}} format.
"""
import json
from typing import TYPE_CHECKING, Optional, Dict, Any, List

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
    
    Handles nested braces and proper JSON parsing. Parsing can be delegated to
    a provider-aware JSON tool parser supplied via ParserConfig.
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

                full_json = self.context.get_current_segment_content()
                tool_call = self._parse_json_tool_call(full_json)

                if tool_call:
                    self.context.update_current_segment_metadata(
                        tool_name=tool_call.get("name", "unknown"),
                        arguments=tool_call.get("arguments", {})
                    )

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

    def _parse_json_tool_call(self, json_str: str) -> Optional[Dict[str, Any]]:
        """
        Parse a JSON string into tool call info.

        Returns dict with 'name' and 'arguments', or None if invalid.
        """
        parser = self.context.json_tool_parser
        if parser is not None:
            parsed_calls = parser.parse(json_str)
            if parsed_calls:
                return parsed_calls[0]
            return None

        try:
            data = json.loads(json_str)

            # Handle array format
            if isinstance(data, list) and len(data) > 0:
                data = data[0]

            if isinstance(data, dict):
                # Extract tool name from various formats
                name = (
                    data.get("name")
                    or data.get("tool")
                    or data.get("function", {}).get("name")
                    or "unknown"
                )

                # Extract arguments from various formats
                arguments = (
                    data.get("arguments")
                    or data.get("parameters")
                    or data.get("function", {}).get("arguments")
                    or {}
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
        
        if self.context.has_more_chars():
            remaining = self.context.consume_remaining()
            if remaining:
                self.context.emit_segment_content(remaining)

        if self._segment_started:
            self.context.emit_segment_end()
        self.context.transition_to(TextState(self.context))
