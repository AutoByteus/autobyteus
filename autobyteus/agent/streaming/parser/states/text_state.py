"""
TextState: Default state for parsing plain text.

This state consumes characters as text content and detects triggers
for transitioning to specialized parsing states (XML tags, JSON).
"""
from typing import TYPE_CHECKING

from .base_state import BaseState
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
        
        start_pos = self.context.get_position()

        if not self.context.has_more_chars():
            return

        strategies = self.context.detection_strategies

        best_idx = -1
        best_strategy = None
        for strategy in strategies:
            idx = strategy.next_marker(self.context, start_pos)
            if idx == -1:
                continue
            if best_idx == -1 or idx < best_idx:
                best_idx = idx
                best_strategy = strategy

        if best_idx == -1:
            text = self.context.substring(start_pos)
            if text:
                self.context.append_text_segment(text)
            self.context.set_position(self.context.get_buffer_length())
            return

        if best_idx > start_pos:
            text = self.context.substring(start_pos, best_idx)
            if text:
                self.context.append_text_segment(text)

        self.context.set_position(best_idx)

        if best_strategy is None:
            self.context.transition_to(XmlTagInitializationState(self.context))
        else:
            self.context.transition_to(best_strategy.create_state(self.context))
        
    def finalize(self) -> None:
        """
        Called when stream ends while in TextState.
        
        Nothing special to do here since run() already emits text
        when buffer is exhausted.
        """
        pass
