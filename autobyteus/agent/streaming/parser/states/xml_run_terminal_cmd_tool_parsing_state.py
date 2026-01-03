"""
XmlRunTerminalCmdToolParsingState: Parses <tool name="run_terminal_cmd"> blocks.

This state specializes the generic XmlToolParsingState to handle terminal command
execution semantics, specifically ensuring 'command' arguments are parsed
and content is streamed appropriately.
"""
from typing import TYPE_CHECKING, Optional, Dict, Any

from .xml_tool_parsing_state import XmlToolParsingState
from ..events import SegmentType

if TYPE_CHECKING:
    from ..parser_context import ParserContext


class XmlRunTerminalCmdToolParsingState(XmlToolParsingState):
    """
    Parses <tool name="run_terminal_cmd"> tool calls.
    
    This state operates identically to XmlToolParsingState but provides
    a distinct type (RUN_TERMINAL_CMD) and specialized metadata handling if needed.
    """
    
    SEGMENT_TYPE = SegmentType.RUN_TERMINAL_CMD
    
    def __init__(self, context: "ParserContext", opening_tag: str):
        super().__init__(context, opening_tag)
        if self._tool_name != "run_terminal_cmd":
            pass
            
        self._found_content_start = False
        self._content_buffering = "" 
        self._captured_args = {}
        self._swallowing_remaining = False
        
    def run(self) -> None:
        """
        Custom run loop to stream ONLY the command argument.
        """
        from .text_state import TextState
        
        if self._swallowing_remaining:
            self._handle_swallowing()
            return

        if not self._segment_started:
            self.context.emit_segment_start(self.SEGMENT_TYPE, **self._get_start_metadata())
            self._segment_started = True

        if not self.context.has_more_chars():
            return

        chunk = self.context.consume_remaining()
        
        if not self._found_content_start:
            self._content_buffering += chunk
            
            import re
            # Look for command start
            match = re.search(r'<arg\s+name=["\']command["\']>', self._content_buffering, re.IGNORECASE)
            
            if match:
                self._found_content_start = True
                end_of_tag = match.end()
                
                real_content = self._content_buffering[end_of_tag:]
                self._content_buffering = "" 
                self._process_content_chunk(real_content)
            else:
                if "</tool>" in self._content_buffering:
                    self._on_segment_complete() 
                    self.context.emit_segment_end()
                    self.context.transition_to(TextState(self.context))
        else:
            self._process_content_chunk(chunk)

    def _process_content_chunk(self, chunk: str) -> None:
        """Process content chunk, stripping closing tags."""
        
        closing_tag = "</arg>"
        combined = self._tail + chunk
        
        idx = combined.find(closing_tag)
        if idx != -1:
            actual_content = combined[:idx]
            if actual_content:
                self.context.emit_segment_content(actual_content)
            
            self._tail = ""
            remainder = combined[idx + len(closing_tag):]
            self._content_buffering = remainder 
            self._swallowing_remaining = True
            
            self._handle_swallowing()
            return
            
        holdback_len = len(closing_tag) - 1
        if len(combined) > holdback_len:
            safe = combined[:-holdback_len]
            self.context.emit_segment_content(safe)
            self._tail = combined[-holdback_len:]
        else:
            self._tail = combined

    def _handle_swallowing(self) -> None:
        """Consume stream until </tool> is found."""
        from .text_state import TextState
        
        self._content_buffering += self.context.consume_remaining()
        
        closing_tag = "</tool>"
        idx = self._content_buffering.find(closing_tag)
        
        if idx != -1:
            remainder = self._content_buffering[idx + len(closing_tag):]
            
            self._on_segment_complete()
            self.context.emit_segment_end()
            self.context.transition_to(TextState(self.context))
            
            if remainder:
                self.context.append_text_segment(remainder)
        else:
            holdback_len = len(closing_tag) - 1
            if len(self._content_buffering) > holdback_len:
                self._content_buffering = self._content_buffering[-holdback_len:]

    def _on_segment_complete(self) -> None:
        # Retrieve the streamed content which is the command
        final_args = {
            "command": self.context.get_current_segment_content()
        }
        self.context.update_current_segment_metadata(arguments=final_args)
