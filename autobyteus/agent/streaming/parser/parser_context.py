"""
ParserContext: Holds the shared state for the streaming parser state machine.

This class manages the scanner, current state, and configuration.
Event emission is delegated to the EventEmitter.
States use this context to read characters, emit events, and transition.
"""
from typing import Optional, List, Dict, Any, TYPE_CHECKING, Literal

from .stream_scanner import StreamScanner
from .event_emitter import EventEmitter
from .events import PartEvent

if TYPE_CHECKING:
    from .states.base_state import BaseState


class ParserConfig:
    """Configuration for the streaming parser."""
    
    # Default patterns for JSON tool call detection
    DEFAULT_JSON_PATTERNS = [
        '{"name"',
        '{"tool"',
        '{"function"',
        '[{"name"',
        '[{"tool"'
    ]
    
    def __init__(
        self,
        parse_tool_calls: bool = True,
        use_xml_tool_format: bool = True,
        json_tool_patterns: Optional[List[str]] = None,
    ):
        self.parse_tool_calls = parse_tool_calls
        self.use_xml_tool_format = use_xml_tool_format
        self.json_tool_patterns = json_tool_patterns or self.DEFAULT_JSON_PATTERNS.copy()


class ParserContext:
    """
    Holds the shared state for the streaming parser state machine.
    
    This context provides:
    - Scanner for reading the character stream
    - EventEmitter for part events
    - State management for transitions
    - Configuration access
    """
    
    def __init__(self, config: Optional[ParserConfig] = None):
        """
        Initialize the parser context.
        
        Args:
            config: Parser configuration. Uses defaults if not provided.
        """
        self._config = config or ParserConfig()
        self._scanner = StreamScanner()
        self._emitter = EventEmitter()
        self._current_state: Optional["BaseState"] = None

    @property
    def config(self) -> ParserConfig:
        """Get the parser configuration."""
        return self._config

    @property
    def parse_tool_calls(self) -> bool:
        """Whether to parse tool calls."""
        return self._config.parse_tool_calls

    @property
    def use_xml_tool_format(self) -> bool:
        """Whether to use XML format for tools."""
        return self._config.use_xml_tool_format

    @property
    def json_tool_patterns(self) -> List[str]:
        """Get the JSON tool call patterns."""
        return self._config.json_tool_patterns

    # --- State Management ---
    
    @property
    def current_state(self) -> "BaseState":
        """Get the current state."""
        if self._current_state is None:
            raise RuntimeError("No current state is set.")
        return self._current_state

    @current_state.setter
    def current_state(self, state: "BaseState") -> None:
        """Set the current state."""
        self._current_state = state

    def transition_to(self, new_state: "BaseState") -> None:
        """Transition to a new state."""
        self._current_state = new_state

    # --- Scanner Delegation ---
    
    def append(self, text: str) -> None:
        """Append text to the scanner buffer."""
        self._scanner.append(text)

    def peek_char(self) -> Optional[str]:
        """Peek at the current character without advancing."""
        return self._scanner.peek()

    def advance(self) -> None:
        """Advance the cursor by one position."""
        self._scanner.advance()

    def advance_by(self, count: int) -> None:
        """Advance the cursor by multiple positions."""
        self._scanner.advance_by(count)

    def has_more_chars(self) -> bool:
        """Check if there are more characters to read."""
        return self._scanner.has_more_chars()

    def get_position(self) -> int:
        """Get the current cursor position."""
        return self._scanner.get_position()

    def set_position(self, position: int) -> None:
        """Set the cursor position."""
        self._scanner.set_position(position)

    def rewind_by(self, count: int) -> None:
        """
        Rewind the cursor by a specified number of positions.
        
        This is an explicit helper for the common rewind-and-transition pattern.
        
        Args:
            count: Number of positions to rewind.
        """
        new_pos = max(0, self._scanner.get_position() - count)
        self._scanner.set_position(new_pos)

    def substring(self, start: int, end: Optional[int] = None) -> str:
        """Extract a substring from the buffer."""
        return self._scanner.substring(start, end)

    # --- Event Emission (Delegated to EventEmitter) ---
    
    def emit_part_start(self, part_type: Literal["text", "tool_call", "reasoning"], **metadata) -> str:
        """Emit a PartStartEvent."""
        return self._emitter.emit_part_start(part_type, **metadata)

    def emit_part_delta(self, delta: str) -> None:
        """Emit a PartDeltaEvent."""
        self._emitter.emit_part_delta(delta)

    def emit_part_end(self) -> Optional[str]:
        """Emit a PartEndEvent."""
        return self._emitter.emit_part_end()

    def get_current_part_id(self) -> Optional[str]:
        """Get the ID of the currently active part."""
        return self._emitter.get_current_part_id()

    def get_current_part_type(self) -> Optional[str]:
        """Get the type of the currently active part."""
        return self._emitter.get_current_part_type()

    def get_current_part_content(self) -> str:
        """Get the accumulated content of the current part."""
        return self._emitter.get_current_part_content()

    def get_current_part_metadata(self) -> Dict[str, Any]:
        """Get the metadata of the current part."""
        return self._emitter.get_current_part_metadata()

    def update_current_part_metadata(self, **metadata) -> None:
        """Update metadata for the current part."""
        self._emitter.update_current_part_metadata(**metadata)

    def get_and_clear_events(self) -> List[PartEvent]:
        """Get all queued events and clear the queue."""
        return self._emitter.get_and_clear_events()

    def get_events(self) -> List[PartEvent]:
        """Get all queued events without clearing."""
        return self._emitter.get_events()

    def append_text_part(self, text: str) -> None:
        """Convenience method to emit a complete text part."""
        self._emitter.append_text_part(text)
