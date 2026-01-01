"""
BaseState: Abstract base class for parser state machine states.

All states in the streaming parser inherit from this class and implement
the run() and finalize() methods.
"""
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..parser_context import ParserContext


class BaseState(ABC):
    """
    Abstract base class for all parser states.
    
    Each state is responsible for:
    1. Processing characters from the context's scanner
    2. Emitting appropriate SegmentEvents
    3. Transitioning to other states when triggers are detected
    """
    
    def __init__(self, context: "ParserContext"):
        """
        Initialize the state with a reference to the parser context.
        
        Args:
            context: The shared parser context.
        """
        self._context = context

    @property
    def context(self) -> "ParserContext":
        """Get the parser context."""
        return self._context

    @abstractmethod
    def run(self) -> None:
        """
        Main processing loop for this state.
        
        This method should:
        - Read characters from context.peek_char()
        - Emit events via context.emit_segment_*()
        - Transition to other states via context.transition_to()
        - Return when no more characters or when transitioning
        """
        pass

    def finalize(self) -> None:
        """
        Called when the stream ends while in this state.
        
        This method should clean up any pending buffers and ensure
        all accumulated content is properly emitted as events.
        
        Default implementation does nothing. Override if needed.
        """
        pass
