"""
XmlWriteFileToolParsingState: Parses <tool name="write_file"> blocks.

This state specializes the generic XmlToolParsingState to handle file writing
semantics, specifically ensuring 'path' and 'content' arguments are parsed
and content is streamed appropriately.
"""
from typing import TYPE_CHECKING, Optional, Dict, Any

from .xml_tool_parsing_state import XmlToolParsingState
from ..events import SegmentType

if TYPE_CHECKING:
    from ..parser_context import ParserContext


class XmlWriteFileToolParsingState(XmlToolParsingState):
    """
    Parses <tool name="write_file"> tool calls.
    
    This state operates identically to XmlToolParsingState but provides
    a distinct type (WRITE_FILE) and specialized metadata handling if needed.
    """
    
    SEGMENT_TYPE = SegmentType.WRITE_FILE
    
    def __init__(self, context: "ParserContext", opening_tag: str):
        super().__init__(context, opening_tag)
        if self._tool_name != "write_file":
            pass
            
        # Internal state for streaming
        self._found_content_start = False
        self._content_buffering = "" 
        self._captured_path: Optional[str] = None
        self._defer_start = True # New flag to defer emission
        self._swallowing_remaining = False # New flag to swallow closing tags
        
    def run(self) -> None:
        """
        Custom run loop to stream ONLY the content argument.
        """
        from .text_state import TextState
        
        if self._swallowing_remaining:
            self._handle_swallowing()
            return

        # Note: We do NOT emit start immediately anymore.
        
        if not self.context.has_more_chars():
            return

        chunk = self.context.consume_remaining()
        
        if not self._found_content_start:
            self._content_buffering += chunk
            
            import re
            
            # 1. Try to find path if missing
            if not self._captured_path:
                path_match = re.search(r'<arg\s+name=["\']path["\']>([^<]+)</arg>', self._content_buffering, re.IGNORECASE)
                if path_match:
                    self._captured_path = path_match.group(1).strip()
                    # Now we have path, we can emit start if we were waiting for it
                    if self._defer_start and not self._segment_started:
                        # Construct metadata with path
                        meta = self._get_start_metadata()
                        meta["path"] = self._captured_path
                        self.context.emit_segment_start(self.SEGMENT_TYPE, **meta)
                        self._segment_started = True
                        self._defer_start = False

            # 2. Look for content start
            match = re.search(r'<arg\s+name=["\']content["\']>', self._content_buffering, re.IGNORECASE)
            
            if match:
                self._found_content_start = True
                end_of_tag = match.end()
                
                # If we still haven't emitted start (e.g. no path found but content started), emit now without path
                if not self._segment_started:
                    self.context.emit_segment_start(self.SEGMENT_TYPE, **self._get_start_metadata())
                    self._segment_started = True
                
                # Update path in metadata if we found it late (redundant but safe)
                if self._captured_path:
                    self.context.update_current_segment_metadata(path=self._captured_path)
                
                real_content = self._content_buffering[end_of_tag:]
                self._content_buffering = "" 
                self._process_content_chunk(real_content)
            else:
                # If closing tool and still no content
                if "</tool>" in self._content_buffering:
                    # If start never happened, force it
                     if not self._segment_started:
                        self.context.emit_segment_start(self.SEGMENT_TYPE, **self._get_start_metadata())
                        self._segment_started = True
                        
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
            
            # We found the end of the content argument.
            # Instead of stopping, we switch to swallowing mode to eat </arguments></tool>
            self._tail = ""
            remainder = combined[idx + len(closing_tag):]
            self._content_buffering = remainder # buffer the rest
            self._swallowing_remaining = True
            
            # Immediately try to finish if we have the closing tags
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
        
        # Add any new data to buffer
        self._content_buffering += self.context.consume_remaining()
        
        closing_tag = "</tool>"
        idx = self._content_buffering.find(closing_tag)
        
        if idx != -1:
            # We found the end!
            # We are done with this tool.
            
            # Anything after </tool> belongs to the next state (TextState)
            remainder = self._content_buffering[idx + len(closing_tag):]
            
            self._on_segment_complete()
            self.context.emit_segment_end()
            self.context.transition_to(TextState(self.context))
            
            # Inject remainder back into the stream for TextState to pick up
            if remainder:
                self.context.append_text_segment(remainder)
        else:
            # Nothing yet, keep swallowing (clearing buffer to avoid memory issues if valid)
            # But we need to keep a holdback in case </tool> is split?
            # </tool> is 7 chars.
            holdback_len = len(closing_tag) - 1
            if len(self._content_buffering) > holdback_len:
                # Discard safe prefix
                self._content_buffering = self._content_buffering[-holdback_len:]

    def _on_segment_complete(self) -> None:
        final_args = {}
        if self._captured_path:
            final_args["path"] = self._captured_path
        
        final_args["content"] = self.context.get_current_segment_content()
        self.context.update_current_segment_metadata(arguments=final_args)

