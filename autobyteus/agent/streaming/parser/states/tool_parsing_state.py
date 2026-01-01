"""
ToolParsingState: Parses <tool name="...">...</tool> blocks.

This state handles tool call parsing, extracting tool name and arguments.

DESIGN: Independent state with its own run() logic for maximum flexibility.
Buffer handling uses position tracking to avoid content loss across chunks.
"""
import re
from typing import TYPE_CHECKING, Optional, Dict, Any

from .base_state import BaseState

if TYPE_CHECKING:
    from ..parser_context import ParserContext


class ToolParsingState(BaseState):
    """
    Parses tool call blocks.
    
    Expected format: <tool name="..."><arg>value</arg></tool>
    
    Supports two argument formats:
    1. Wrapped: <arguments><arg1>value1</arg1></arguments>
    2. Direct: <arg1>value1</arg1><arg2>value2</arg2>
    
    The state:
    1. Extracts tool name from the opening tag
    2. Parses arguments within the content
    3. Emits SEGMENT_START with tool metadata
    4. Streams raw content for real-time display
    5. Emits SEGMENT_END when </tool> is found
    """
    
    # Pattern to extract tool name
    NAME_PATTERN = re.compile(r'name\s*=\s*["\']([^"\']+)["\']', re.IGNORECASE)
    CLOSING_TAG = "</tool>"
    ARGS_OPEN = "<arguments>"
    ARGS_CLOSE = "</arguments>"
    
    def __init__(self, context: "ParserContext", opening_tag: str):
        """
        Initialize the tool parsing state.
        
        Args:
            context: The parser context.
            opening_tag: The complete opening tag (e.g., '<tool name="read_file">').
        """
        super().__init__(context)
        self._opening_tag = opening_tag
        self._content_buffer = ""      # Full content for parsing
        self._emitted_length = 0       # Track how much has been streamed
        self._tool_name: Optional[str] = None
        self._segment_started = False
        self._parsed_arguments: Dict[str, Any] = {}
        
        # Extract tool name from opening tag
        match = self.NAME_PATTERN.search(opening_tag)
        if match:
            self._tool_name = match.group(1)

    def run(self) -> None:
        """
        Parse tool content from the stream.
        """
        from .text_state import TextState
        
        # Start the segment (first run only)
        if not self._segment_started:
            if self._tool_name:
                self.context.emit_part_start(
                    "tool_call",
                    tool_name=self._tool_name
                )
                self._segment_started = True
            else:
                # No tool name - treat as text
                self.context.append_text_part(self._opening_tag)
                self.context.transition_to(TextState(self.context))
                return
        
        while self.context.has_more_chars():
            char = self.context.peek_char()
            self._content_buffer += char
            self.context.advance()
            
            lower_buffer = self._content_buffer.lower()
            
            # Check for closing tag
            if lower_buffer.endswith(self.CLOSING_TAG.lower()):
                # Remove closing tag from content
                content = self._content_buffer[:-len(self.CLOSING_TAG)]
                
                # Parse arguments from FULL content
                self._parse_arguments_from_content(content)
                
                # Emit any remaining content not yet streamed
                unemitted = content[self._emitted_length:]
                if unemitted:
                    self.context.emit_part_delta(unemitted)
                
                # Update metadata with parsed arguments
                self.context.update_current_part_metadata(
                    arguments=self._parsed_arguments
                )
                
                self.context.emit_part_end()
                self.context.transition_to(TextState(self.context))
                return
        
        # Buffer exhausted but tool not complete
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
                self.context.emit_part_delta(unemitted)
                self._emitted_length = safe_length

    def _parse_arguments_from_content(self, content: str) -> None:
        """
        Parse XML arguments from the content.
        
        Supports two formats:
        1. Wrapped: <arguments><arg1>value1</arg1></arguments>
        2. Direct: <arg1>value1</arg1><arg2>value2</arg2>
        """
        # Simple regex-based argument extraction
        args_match = re.search(
            rf'{self.ARGS_OPEN}(.*?){self.ARGS_CLOSE}',
            content,
            re.IGNORECASE | re.DOTALL
        )
        
        if args_match:
            args_content = args_match.group(1)
        else:
            # No <arguments> wrapper - parse directly from content
            args_content = content.strip()
        
        # Extract individual arguments using regex
        arg_pattern = re.compile(r'<(\w+)>(.*?)</\1>', re.DOTALL)
        for match in arg_pattern.finditer(args_content):
            arg_name = match.group(1)
            arg_value = match.group(2).strip()
            self._parsed_arguments[arg_name] = arg_value

    def finalize(self) -> None:
        """
        Called when stream ends while parsing a tool.
        
        Emit any remaining content and close the segment.
        """
        from .text_state import TextState
        
        if not self._segment_started:
            # Never started - emit opening tag as text
            self.context.append_text_part(self._opening_tag)
        else:
            # Emit remaining content
            unemitted = self._content_buffer[self._emitted_length:]
            if unemitted:
                self.context.emit_part_delta(unemitted)
            
            # Close the segment
            self.context.emit_part_end()
        
        self.context.transition_to(TextState(self.context))
