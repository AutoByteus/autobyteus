"""
ParserContext: Holds the shared state for the streaming parser state machine.

This class manages the scanner, current state, and configuration.
Event emission is delegated to the EventEmitter.
States use this context to read characters, emit events, and transition.
"""
from typing import Optional, List, Dict, Any, TYPE_CHECKING

from .stream_scanner import StreamScanner
from .event_emitter import EventEmitter
from .events import SegmentEvent, SegmentType

if TYPE_CHECKING:
    from .states.base_state import BaseState
    from .json_parsing_strategies.base import JsonToolParsingStrategy


class ParserConfig:
    """Configuration for the streaming parser."""
    
    # Default patterns for JSON tool call detection
    DEFAULT_JSON_PATTERNS = [
        '{"tool"',
        '{"tool_calls"',
        '{"tools"',
        '{"function"',
        '{"name"',
        '[{"tool"',
        '[{"function"',
        '[{"name"'
    ]
    
    def __init__(
        self,
        parse_tool_calls: bool = True,
        json_tool_patterns: Optional[List[str]] = None,
        json_tool_parser: Optional["JsonToolParsingStrategy"] = None,
        strategy_order: Optional[List[str]] = None,
        segment_id_prefix: Optional[str] = None,
    ):
        self.parse_tool_calls = parse_tool_calls
        self.json_tool_patterns = json_tool_patterns or self.DEFAULT_JSON_PATTERNS.copy()
        self.json_tool_parser = json_tool_parser
        self.strategy_order = strategy_order or ["xml_tag"]
        self.segment_id_prefix = segment_id_prefix


class ParserContext:
    """
    Holds the shared state for the streaming parser state machine.
    
    This context provides:
    - Scanner for reading the character stream
    - EventEmitter for segment events
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
        self._emitter = EventEmitter(segment_id_prefix=self._config.segment_id_prefix)
        self._current_state: Optional["BaseState"] = None
        from .strategies.registry import create_detection_strategies
        self._strategies = create_detection_strategies(self._config.strategy_order)

    @property
    def config(self) -> ParserConfig:
        """Get the parser configuration."""
        return self._config

    @property
    def parse_tool_calls(self) -> bool:
        """Whether to parse tool calls."""
        return self._config.parse_tool_calls

    @property
    def json_tool_patterns(self) -> List[str]:
        """Get the JSON tool call patterns."""
        return self._config.json_tool_patterns

    @property
    def json_tool_parser(self) -> Optional["JsonToolParsingStrategy"]:
        """Get the JSON tool parser strategy if configured."""
        return self._config.json_tool_parser

    @property
    def detection_strategies(self):
        """Get the ordered detection strategies."""
        return self._strategies

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

    def get_buffer_length(self) -> int:
        """Get the total buffer length."""
        return self._scanner.get_buffer_length()

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

    def find(self, sub: str, start: Optional[int] = None) -> int:
        """Find a substring in the buffer."""
        return self._scanner.find(sub, start)

    def consume(self, count: int) -> str:
        """Consume a number of characters from the buffer."""
        return self._scanner.consume(count)

    def consume_remaining(self) -> str:
        """Consume all remaining characters from the buffer."""
        return self._scanner.consume_remaining()

    def compact(self, min_prefix: int = 65536) -> None:
        """Compact the scanner buffer."""
        self._scanner.compact(min_prefix=min_prefix)

    # --- Event Emission (Delegated to EventEmitter) ---
    
    def emit_segment_start(self, segment_type: SegmentType, **metadata) -> str:
        """Emit a SEGMENT_START event."""
        return self._emitter.emit_segment_start(segment_type, **metadata)

    def emit_segment_content(
        self,
        delta: Any,
        arg_name: Optional[str] = None,
        arg_state: Optional[str] = None,
    ) -> None:
        """Emit a SEGMENT_CONTENT event with optional argument context."""
        self._emitter.emit_segment_content(delta, arg_name, arg_state)

    def emit_segment_end(self) -> Optional[str]:
        """Emit a SEGMENT_END event."""
        return self._emitter.emit_segment_end()

    def get_current_segment_id(self) -> Optional[str]:
        """Get the ID of the currently active segment."""
        return self._emitter.get_current_segment_id()

    def get_current_segment_type(self) -> Optional[SegmentType]:
        """Get the type of the currently active segment."""
        return self._emitter.get_current_segment_type()

    def get_current_segment_content(self) -> str:
        """Get the accumulated content of the current segment."""
        return self._emitter.get_current_segment_content()

    def get_current_segment_metadata(self) -> Dict[str, Any]:
        """Get the metadata of the current segment."""
        return self._emitter.get_current_segment_metadata()

    def update_current_segment_metadata(self, **metadata) -> None:
        """Update metadata for the current segment."""
        self._emitter.update_current_segment_metadata(**metadata)

    def get_and_clear_events(self) -> List[SegmentEvent]:
        """Get all queued events and clear the queue."""
        return self._emitter.get_and_clear_events()

    def get_events(self) -> List[SegmentEvent]:
        """Get all queued events without clearing."""
        return self._emitter.get_events()

    def append_text_segment(self, text: str) -> None:
        """Append text content to the current text segment, starting one if needed."""
        self._emitter.append_text_segment(text)
