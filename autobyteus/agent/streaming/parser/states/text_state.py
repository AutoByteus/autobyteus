"""
TextState: Default state for parsing plain text.

This state consumes characters as text content and detects triggers
for transitioning to specialized parsing states (XML tags, JSON).
"""
from typing import TYPE_CHECKING

from .base_state import BaseState
from ..events import SegmentType

if TYPE_CHECKING:
    from ..parser_context import ParserContext


class TextState(BaseState):
    """
    Default state for parsing plain text content.
    
    This state:
    - Accumulates text characters
    - Detects '<' for potential XML tag transitions
    - Detects '{' or '[' for potential JSON transitions (if enabled)
    - Emits text segments when transitioning or at end of buffer
    """
    
    def __init__(self, context: "ParserContext"):
        super().__init__(context)

    def run(self) -> None:
        """
        Process characters as text until a trigger is found or buffer is exhausted.
        """
        # Import here to avoid circular dependency
        from .xml_tag_initialization_state import XmlTagInitializationState
        from .json_initialization_state import JsonInitializationState
        
        start_pos = self.context.get_position()
        
        while self.context.has_more_chars():
            char = self.context.peek_char()
            
            # Check for XML tag start (always active)
            if char == '<':
                # Emit accumulated text before transitioning
                text = self.context.substring(start_pos, self.context.get_position())
                if text:
                    self.context.append_text_segment(text)
                
                # Transition to XML tag initialization
                self.context.transition_to(XmlTagInitializationState(self.context))
                return
            
            # Check for JSON start (only if tool parsing enabled and not using XML format)
            if (self.context.parse_tool_calls and 
                not self.context.use_xml_tool_format and 
                char in ('{', '[')):
                # Emit accumulated text before transitioning
                text = self.context.substring(start_pos, self.context.get_position())
                if text:
                    self.context.append_text_segment(text)
                
                # Transition to JSON initialization
                self.context.transition_to(JsonInitializationState(self.context))
                return
            
            # Regular character - continue accumulating
            self.context.advance()
        
        # Buffer exhausted - emit any accumulated text
        text = self.context.substring(start_pos)
        if text:
            self.context.append_text_segment(text)

    def finalize(self) -> None:
        """
        Called when stream ends while in TextState.
        
        Nothing special to do here since run() already emits text
        when buffer is exhausted.
        """
        pass
