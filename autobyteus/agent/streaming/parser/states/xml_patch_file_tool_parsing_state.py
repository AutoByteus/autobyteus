"""
XmlPatchFileToolParsingState: Streams <tool name="patch_file"> blocks.

This state specializes the generic XmlToolParsingState to stream patch/diff content
and capture the path for display. Argument parsing is handled later by the
ToolInvocationAdapter.
"""
from typing import TYPE_CHECKING, Optional

from .xml_tool_parsing_state import XmlToolParsingState
from ..events import SegmentType

if TYPE_CHECKING:
    from ..parser_context import ParserContext


class XmlPatchFileToolParsingState(XmlToolParsingState):
    """
    Streams <tool name="patch_file"> tool calls.
    
    This state operates similarly to XmlWriteFileToolParsingState but provides
    a distinct type (PATCH_FILE) for unified diff content streaming.
    
    Key differences from write_file:
    - Content arg name: 'patch' instead of 'content'
    - Sentinel markers: __START_PATCH__ / __END_PATCH__
    - Segment type: PATCH_FILE
    """
    
    SEGMENT_TYPE = SegmentType.PATCH_FILE
    START_CONTENT_MARKER = "__START_PATCH__"
    END_CONTENT_MARKER = "__END_PATCH__"
    CONTENT_ARG_CLOSE_TAG = "</arg>"
    
    def __init__(self, context: "ParserContext", opening_tag: str):
        super().__init__(context, opening_tag)
        if self._tool_name != "patch_file":
            pass
            
        # Internal state for streaming
        self._found_content_start = False
        self._content_buffering = "" 
        self._captured_path: Optional[str] = None
        self._defer_start = True  # Defer emission until path is found
        self._swallowing_remaining = False  # Swallow closing tags
        self._content_mode = "seek_marker"
        self._content_seek_buffer = ""
        self._marker_tail = ""
        
    def run(self) -> None:
        """
        Custom run loop to stream ONLY the patch argument content.
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

            # 2. Look for patch content start (note: arg name is 'patch', not 'content')
            match = re.search(r'<arg\s+name=["\']patch["\']>', self._content_buffering, re.IGNORECASE)
            
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
                self._content_mode = "seek_marker"
                self._content_seek_buffer = ""
                self._marker_tail = ""
                self._tail = ""
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
        """Process content chunk, supporting optional content markers."""
        if not chunk:
            return

        if self._content_mode == "marker":
            self._process_marker_content(chunk)
            return

        if self._content_mode == "default":
            self._process_default_content(chunk)
            return

        self._process_seek_marker_content(chunk)

    def _process_seek_marker_content(self, chunk: str) -> None:
        """Seek __START_PATCH__ before committing to default parsing."""
        self._content_seek_buffer += chunk

        start_idx = self._content_seek_buffer.find(self.START_CONTENT_MARKER)
        if start_idx != -1:
            after_start = self._content_seek_buffer[start_idx + len(self.START_CONTENT_MARKER):]
            # Strip leading newline after marker to avoid empty first line
            if after_start.startswith("\n"):
                after_start = after_start[1:]
            self._content_seek_buffer = ""
            self._content_mode = "marker"
            self._marker_tail = ""
            self._tail = ""
            if after_start:
                self._process_marker_content(after_start)
            return

        closing_idx = self._content_seek_buffer.find(self.CONTENT_ARG_CLOSE_TAG)
        if closing_idx != -1:
            buffered = self._content_seek_buffer
            self._content_seek_buffer = ""
            self._content_mode = "default"
            self._tail = ""
            self._process_default_content(buffered)
            return

        stripped = self._content_seek_buffer.lstrip()
        if stripped and not self.START_CONTENT_MARKER.startswith(stripped):
            buffered = self._content_seek_buffer
            self._content_seek_buffer = ""
            self._content_mode = "default"
            self._tail = ""
            self._process_default_content(buffered)

    def _process_default_content(self, chunk: str) -> None:
        """Process content chunk, stripping closing tags."""
        closing_tag = self.CONTENT_ARG_CLOSE_TAG
        combined = self._tail + chunk

        idx = combined.find(closing_tag)

        if idx != -1:
            actual_content = combined[:idx]
            if actual_content:
                self.context.emit_segment_content(actual_content)

            # We found the end of the content argument.
            # Switch to swallowing mode to eat </arguments></tool>
            self._tail = ""
            remainder = combined[idx + len(closing_tag):]
            self._content_buffering = remainder
            self._swallowing_remaining = True

            # Immediately try to finish if we have the closing tags
            self._handle_swallowing()
            return

        holdback_len = len(closing_tag) - 1
        if len(combined) > holdback_len:
            safe = combined[:-holdback_len]
            if safe:
                self.context.emit_segment_content(safe)
            self._tail = combined[-holdback_len:]
        else:
            self._tail = combined

    def _process_marker_content(self, chunk: str) -> None:
        """Process content chunk when inside __START_PATCH__/__END_PATCH__ markers."""
        combined = self._marker_tail + chunk
        end_marker = self.END_CONTENT_MARKER
        closing_tag = self.CONTENT_ARG_CLOSE_TAG

        # Priority 1: Check for the explicit end marker
        idx = combined.find(end_marker)
        if idx != -1:
            actual_content = combined[:idx]
            if actual_content:
                self.context.emit_segment_content(actual_content)

            self._marker_tail = ""
            remainder = combined[idx + len(end_marker):]
            self._content_buffering = remainder
            self._swallowing_remaining = True
            self._handle_swallowing()
            return

        # Priority 2: Check for closing arg tag as fallback (missing sentinel case)
        idx_close = combined.find(closing_tag)
        if idx_close != -1:
            remainder_after_close = combined[idx_close + len(closing_tag):]
            
            import re
            # Check if followed by standard XML closure (ignoring whitespace)
            
            is_valid_closure = False
            if re.match(r'^\s*(?:</arguments>|</tool>)', remainder_after_close):
                is_valid_closure = True
            
            # If we have indeterminate whitespace, we must hold back to be sure
            elif remainder_after_close.strip() == "":
                 self._marker_tail = combined
                 return

            if is_valid_closure:
                actual_content = combined[:idx_close]
                
                # Remove trailing newline for clean file content
                if re.search(r'\n\s*$', actual_content):
                    actual_content = re.sub(r'\n\s*$', '', actual_content)
                
                if actual_content:
                    self.context.emit_segment_content(actual_content)
                
                self._marker_tail = ""
                remainder = combined[idx_close + len(closing_tag):]
                self._content_buffering = remainder
                self._swallowing_remaining = True
                self._handle_swallowing()
                return

        # Holdback logic - hold back enough to detect EITHER marker OR closing_tag + context
        max_holdback = 30  # Safe buffer for regex lookahead
        
        if len(combined) > max_holdback:
            safe = combined[:-max_holdback]
            if safe:
                self.context.emit_segment_content(safe)
            self._marker_tail = combined[-max_holdback:]
        else:
            self._marker_tail = combined

    def _handle_swallowing(self) -> None:
        """Consume stream until </tool> is found."""
        from .text_state import TextState
        
        # Add any new data to buffer
        self._content_buffering += self.context.consume_remaining()
        
        closing_tag = "</tool>"
        idx = self._content_buffering.find(closing_tag)
        
        if idx != -1:
            # We found the end!
            # Anything after </tool> belongs to the next state (TextState)
            remainder = self._content_buffering[idx + len(closing_tag):]
            
            self._on_segment_complete()
            self.context.emit_segment_end()
            self.context.transition_to(TextState(self.context))
            
            # Inject remainder back into the stream for TextState to pick up
            if remainder:
                self.context.append_text_segment(remainder)
        else:
            # Nothing yet, keep swallowing
            holdback_len = len(closing_tag) - 1
            if len(self._content_buffering) > holdback_len:
                # Discard safe prefix
                self._content_buffering = self._content_buffering[-holdback_len:]

    def _on_segment_complete(self) -> None:
        return None
