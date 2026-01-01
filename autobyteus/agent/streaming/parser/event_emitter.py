"""
EventEmitter: Manages part event emission for the streaming parser.

This class is responsible for:
- Generating unique part IDs
- Tracking the current active part
- Building and queuing PartEvents
- Managing the event queue
"""
from typing import Optional, List, Dict, Any, Literal

from .events import PartEvent, PartStartEvent, PartDeltaEvent, PartEndEvent


class EventEmitter:
    """
    Manages part event emission for the streaming parser.
    
    Generates unique IDs and manages the lifecycle of Message Parts (Start -> Delta -> End).
    """
    
    def __init__(self):
        self._event_queue: List[PartEvent] = []
        self._part_counter: int = 0
        self._current_part_id: Optional[str] = None
        self._current_part_type: Optional[str] = None
        self._current_part_content: str = ""
        self._current_part_metadata: Dict[str, Any] = {}

    def _generate_part_id(self) -> str:
        """Generate a unique part ID."""
        self._part_counter += 1
        return f"part_{self._part_counter}"

    def emit_part_start(
        self, 
        part_type: Literal["text", "tool_call", "reasoning"], 
        **metadata
    ) -> str:
        """
        Emit a PartStartEvent and begin tracking a new part.
        
        Args:
            part_type: The type of part starting (text, tool_call, reasoning).
            **metadata: Additional metadata for the part (e.g., tool_name).
            
        Returns:
            The generated part ID.
        """
        part_id = self._generate_part_id()
        self._current_part_id = part_id
        self._current_part_type = part_type
        self._current_part_content = ""
        self._current_part_metadata = dict(metadata)
        
        event = PartStartEvent(
            part_id=part_id, 
            part_type=part_type, 
            metadata=self._current_part_metadata
        )
        self._event_queue.append(event)
        return part_id

    def emit_part_delta(self, delta: str) -> None:
        """
        Emit a PartDeltaEvent for the current part.
        
        Args:
            delta: The content chunk to emit.
            
        Raises:
            RuntimeError: If no part is active.
        """
        if self._current_part_id is None:
            raise RuntimeError("Cannot emit delta without an active part.")
        
        # Accumulate string content
        self._current_part_content += delta
        
        event = PartDeltaEvent(
            part_id=self._current_part_id, 
            delta=delta
        )
        self._event_queue.append(event)

    def emit_part_end(self) -> Optional[str]:
        """
        Emit a PartEndEvent and stop tracking the current part.
        
        The END event includes the *accumulated* metadata (including any updates).
        
        Returns:
            The part ID that was ended, or None if no active part.
        """
        if self._current_part_id is None:
            return None
        
        part_id = self._current_part_id
        
        event = PartEndEvent(
            part_id=part_id,
            metadata=self._current_part_metadata.copy()
        )
        self._event_queue.append(event)
        
        # Clear tracking
        self._current_part_id = None
        self._current_part_type = None
        
        return part_id

    # --- Query Methods ---
    
    def get_current_part_id(self) -> Optional[str]:
        """Get the ID of the currently active part."""
        return self._current_part_id

    def get_current_part_type(self) -> Optional[str]:
        """Get the type of the currently active part."""
        return self._current_part_type

    def get_current_part_content(self) -> str:
        """Get the accumulated content of the current part."""
        return self._current_part_content

    def get_current_part_metadata(self) -> Dict[str, Any]:
        """Get the metadata of the current part."""
        return self._current_part_metadata.copy()

    def update_current_part_metadata(self, **metadata) -> None:
        """Update metadata for the current part."""
        self._current_part_metadata.update(metadata)

    # --- Event Queue Management ---
    
    def get_and_clear_events(self) -> List[PartEvent]:
        """
        Get all queued events and clear the queue.
        
        Returns:
            List of PartEvents that were queued.
        """
        events = self._event_queue.copy()
        self._event_queue.clear()
        return events

    def get_events(self) -> List[PartEvent]:
        """Get all queued events without clearing."""
        return self._event_queue.copy()

    # --- Convenience Methods ---
    
    def append_text_part(self, text: str) -> None:
        """
        Convenience method to emit a complete text part.
        
        Emits START, DELTA, and END events.
        """
        if not text:
            return
        
        self.emit_part_start("text")
        self.emit_part_delta(text)
        self.emit_part_end()
