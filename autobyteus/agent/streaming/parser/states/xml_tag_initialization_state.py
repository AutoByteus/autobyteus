"""
XmlTagInitializationState: Analyzes potential XML tags after a '<' is detected.

This state buffers characters to identify special tags like <tool
and transitions to the appropriate specialized state.

UNIFORM HANDOFF: All content states receive the complete opening_tag and handle
their own initialization consistently.
"""
from typing import TYPE_CHECKING

from .base_state import BaseState

if TYPE_CHECKING:
    from ..parser_context import ParserContext


class XmlTagInitializationState(BaseState):
    """
    Analyzes a potential XML tag to determine the correct specialized state.
    
    This state is entered when a '<' is detected. It buffers characters
    to identify tags like <tool.
    
    If no known tag is detected, the buffered content is emitted as text.
    
    UNIFORM HANDOFF PATTERN:
    All content-parsing states receive (context, opening_tag) and handle
    their own buffer initialization consistently.
    """
    
    # Known tag prefixes (lowercase for case-insensitive matching)
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
        from .tool_parsing_state import ToolParsingState
        
        while self.context.has_more_chars():
            char = self.context.peek_char()
            self._tag_buffer += char
            self.context.advance()
            
            lower_buffer = self._tag_buffer.lower()
            
            # --- Tag completion check (when we see '>') ---
            if char == '>':
                # <tool...> tag (only if tool parsing is enabled)
                if lower_buffer.startswith(self.POSSIBLE_TOOL):
                    if self.context.parse_tool_calls:
                        # UNIFORM HANDOFF: Pass complete opening_tag
                        self.context.transition_to(
                            ToolParsingState(self.context, self._tag_buffer)
                        )
                    else:
                        # Tool parsing disabled - emit as text
                        self.context.append_text_part(self._tag_buffer)
                        self.context.transition_to(TextState(self.context))
                    return
                
                # Unknown tag - emit as text
                self.context.append_text_part(self._tag_buffer)
                self.context.transition_to(TextState(self.context))
                return
            
            # --- Continuity check ---
            # If the buffer can still potentially match a known tag, continue
            could_be_tool = (
                self.POSSIBLE_TOOL.startswith(lower_buffer) or 
                lower_buffer.startswith(self.POSSIBLE_TOOL)
            )
            
            if not could_be_tool:
                # No possible match - emit as text and return to TextState
                self.context.append_text_part(self._tag_buffer)
                self.context.transition_to(TextState(self.context))
                return
        
        # Buffer exhausted but tag incomplete - wait for more data
        # The buffer is preserved in self._tag_buffer for next run()

    def finalize(self) -> None:
        """
        Called when stream ends while in this state.
        
        Emit any buffered content as text.
        """
        from .text_state import TextState
        
        if self._tag_buffer:
            self.context.append_text_part(self._tag_buffer)
            self._tag_buffer = ""
        
        self.context.transition_to(TextState(self.context))

