"""
XmlTagInitializationState: Analyzes potential XML tags after a '<' is detected.

This state buffers characters to identify special tags like <tool, <write_file,
<run_terminal_cmd and transitions to the appropriate specialized state.

UNIFORM HANDOFF: All content states receive the complete opening_tag and handle
their own initialization consistently.
"""
from typing import TYPE_CHECKING

from .base_state import BaseState
from ..events import SegmentType

if TYPE_CHECKING:
    from ..parser_context import ParserContext


class XmlTagInitializationState(BaseState):
    """
    Analyzes a potential XML tag to determine the correct specialized state.
    
    This state is entered when a '<' is detected. It buffers characters
    to identify tags like <tool, <write_file, <run_bash.
    
    If no known tag is detected, the buffered content is emitted as text.
    
    UNIFORM HANDOFF PATTERN:
    All content-parsing states receive (context, opening_tag) and handle
    their own buffer initialization consistently.
    """
    
    # Known tag prefixes (lowercase for case-insensitive matching)
    POSSIBLE_WRITE_FILE = "<write_file"
    POSSIBLE_RUN_BASH = "<run_bash"
    POSSIBLE_TOOL = "<tool"
    
    def __init__(self, context: "ParserContext"):
        super().__init__(context)
        # Consume the '<' that triggered this state
        self.context.advance()
        self._tag_buffer = "<"
    
    def run(self) -> None:
        """
        Buffer characters and identify the tag type.
        
        Transitions to specialized states or reverts to text if unknown.
        """
        from .text_state import TextState
        from .custom_xml_tag_write_file_parsing_state import CustomXmlTagWriteFileParsingState
        from .custom_xml_tag_run_bash_parsing_state import CustomXmlTagRunBashParsingState
        from .xml_tool_parsing_state import XmlToolParsingState
        from .xml_write_file_tool_parsing_state import XmlWriteFileToolParsingState
        from .xml_run_bash_tool_parsing_state import XmlRunBashToolParsingState

        if not self.context.has_more_chars():
            return

        start_pos = self.context.get_position()
        end_idx = self.context.find(">", start_pos)

        if end_idx == -1:
            self._tag_buffer += self.context.consume_remaining()

            lower_buffer = self._tag_buffer.lower()
            could_be_write_file = (
                self.POSSIBLE_WRITE_FILE.startswith(lower_buffer) or 
                lower_buffer.startswith(self.POSSIBLE_WRITE_FILE)
            )
            could_be_run_bash = (
                self.POSSIBLE_RUN_BASH.startswith(lower_buffer) or 
                lower_buffer.startswith(self.POSSIBLE_RUN_BASH)
            )
            could_be_tool = (
                self.POSSIBLE_TOOL.startswith(lower_buffer) or 
                lower_buffer.startswith(self.POSSIBLE_TOOL)
            )

            if not (could_be_write_file or could_be_run_bash or could_be_tool):
                self.context.append_text_segment(self._tag_buffer)
                self.context.transition_to(TextState(self.context))
            return

        self._tag_buffer += self.context.consume(end_idx - start_pos + 1)
        lower_buffer = self._tag_buffer.lower()

        # Handle legacy <write_file> tag
        if lower_buffer.startswith(self.POSSIBLE_WRITE_FILE):
            if self.context.get_current_segment_type() == SegmentType.TEXT:
                self.context.emit_segment_end()
            self.context.transition_to(
                CustomXmlTagWriteFileParsingState(self.context, self._tag_buffer)
            )
            return

        if lower_buffer.startswith(self.POSSIBLE_RUN_BASH):
            if self.context.get_current_segment_type() == SegmentType.TEXT:
                self.context.emit_segment_end()
            self.context.transition_to(
                CustomXmlTagRunBashParsingState(self.context, self._tag_buffer)
            )
            return

        if lower_buffer.startswith(self.POSSIBLE_TOOL):
            if self.context.parse_tool_calls:
                if self.context.get_current_segment_type() == SegmentType.TEXT:
                    self.context.emit_segment_end()
                
                # Check for specialized <tool name="write_file"> or <tool name="run_bash">
                import re
                is_write_file = re.search(r'name\s*=\s*["\']write_file["\']', self._tag_buffer, re.IGNORECASE)
                is_run_term = re.search(r'name\s*=\s*["\']run_bash["\']', self._tag_buffer, re.IGNORECASE)
                
                if is_write_file:
                    self.context.transition_to(
                        XmlWriteFileToolParsingState(self.context, self._tag_buffer)
                    )
                elif is_run_term:
                    self.context.transition_to(
                        XmlRunBashToolParsingState(self.context, self._tag_buffer)
                    )
                else:
                    self.context.transition_to(
                        XmlToolParsingState(self.context, self._tag_buffer)
                    )
            else:
                self.context.append_text_segment(self._tag_buffer)
                self.context.transition_to(TextState(self.context))
            return

        self.context.append_text_segment(self._tag_buffer)
        self.context.transition_to(TextState(self.context))

    def finalize(self) -> None:
        """
        Called when stream ends while in this state.
        
        Emit any buffered content as text.
        """
        from .text_state import TextState
        
        if self._tag_buffer:
            self.context.append_text_segment(self._tag_buffer)
            self._tag_buffer = ""
        
        self.context.transition_to(TextState(self.context))
