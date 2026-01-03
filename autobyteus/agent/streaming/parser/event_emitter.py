"""
EventEmitter: Manages segment event emission for the streaming parser.

This class is responsible for:
- Generating unique segment IDs
- Tracking the current active segment
- Building and queuing SegmentEvents
- Managing the event queue
"""
from typing import Optional, List, Dict, Any
import logging

from .events import SegmentEvent, SegmentType, SegmentEventType

logger = logging.getLogger(__name__)


class EventEmitter:
    """
    Manages segment event emission for the streaming parser.
    
    Extracted from ParserContext to improve single responsibility.
    """
    
    def __init__(self, segment_id_prefix: Optional[str] = None):
        self._event_queue: List[SegmentEvent] = []
        self._segment_counter: int = 0
        self._current_segment_id: Optional[str] = None
        self._current_segment_type: Optional[SegmentType] = None
        self._current_segment_content: str = ""
        self._current_segment_metadata: Dict[str, Any] = {}
        self._segment_id_prefix: Optional[str] = segment_id_prefix

    def _generate_segment_id(self) -> str:
        """Generate a unique segment ID."""
        self._segment_counter += 1
        base_id = f"seg_{self._segment_counter}"
        if self._segment_id_prefix:
            return f"{self._segment_id_prefix}{base_id}"
        return base_id

    def emit_segment_start(
        self, 
        segment_type: SegmentType, 
        **metadata
    ) -> str:
        """
        Emit a SEGMENT_START event and begin tracking a new segment.
        
        Args:
            segment_type: The type of segment starting.
            **metadata: Additional metadata for the segment.
            
        Returns:
            The generated segment ID.
        """
        segment_id = self._generate_segment_id()
        self._current_segment_id = segment_id
        self._current_segment_type = segment_type
        self._current_segment_content = ""
        self._current_segment_metadata = dict(metadata)
        
        event = SegmentEvent.start(segment_id, segment_type, **metadata)
        self._event_queue.append(event)
        return segment_id

    def emit_segment_content(
        self,
        delta: Any,
        arg_name: Optional[str] = None,
        arg_state: Optional[str] = None,
    ) -> None:
        """
        Emit a SEGMENT_CONTENT event for the current segment.
        
        Args:
            delta: The content delta to emit.
            arg_name: Optional argument name context for tool call streaming.
            arg_state: Optional argument boundary state ("start", "delta", "end").
            
        Raises:
            RuntimeError: If no segment is active.
        """
        if self._current_segment_id is None:
            raise RuntimeError("Cannot emit content without an active segment.")
        
        # Accumulate string content
        if isinstance(delta, str):
            self._current_segment_content += delta
        
        event = SegmentEvent.content(self._current_segment_id, delta, arg_name, arg_state)
        self._event_queue.append(event)

    def emit_segment_end(self) -> Optional[str]:
        """
        Emit a SEGMENT_END event and stop tracking the current segment.
        
        The END event includes the current segment metadata for downstream
        processing (e.g., tool invocation creation).
        
        Returns:
            The segment ID that was ended, or None if no active segment.
        """
        if self._current_segment_id is None:
            return None
        
        segment_id = self._current_segment_id
        
        # Include metadata in END event for downstream processing
        event = SegmentEvent(
            event_type=SegmentEventType.END,
            segment_id=segment_id,
            payload={"metadata": self._current_segment_metadata.copy()} if self._current_segment_metadata else {}
        )
        self._event_queue.append(event)
        
        # Clear tracking
        self._current_segment_id = None
        self._current_segment_type = None
        
        return segment_id

    # --- Query Methods ---
    
    def get_current_segment_id(self) -> Optional[str]:
        """Get the ID of the currently active segment."""
        return self._current_segment_id

    def get_current_segment_type(self) -> Optional[SegmentType]:
        """Get the type of the currently active segment."""
        return self._current_segment_type

    def get_current_segment_content(self) -> str:
        """Get the accumulated content of the current segment."""
        return self._current_segment_content

    def get_current_segment_metadata(self) -> Dict[str, Any]:
        """Get the metadata of the current segment."""
        return self._current_segment_metadata.copy()

    def update_current_segment_metadata(self, **metadata) -> None:
        """Update metadata for the current segment."""
        self._current_segment_metadata.update(metadata)

    # --- Event Queue Management ---
    
    def get_and_clear_events(self) -> List[SegmentEvent]:
        """
        Get all queued events and clear the queue.
        
        Returns:
            List of SegmentEvents that were queued.
        """
        events = self._event_queue.copy()
        self._event_queue.clear()
        return events

    def get_events(self) -> List[SegmentEvent]:
        """Get all queued events without clearing."""
        return self._event_queue.copy()

    # --- Convenience Methods ---
    
    def append_text_segment(self, text: str) -> None:
        """
        Convenience method to emit a complete text segment.
        
        Emits START (if needed) and CONTENT events for a text segment.
        The segment remains open until explicitly ended by the caller.
        
        Args:
            text: The text content to emit.
        """
        if not text:
            return

        if self._current_segment_type != SegmentType.TEXT:
            if self._current_segment_id is not None:
                logger.warning(
                    "append_text_segment called while non-text segment is active (%s); "
                    "ending it before starting a text segment.",
                    self._current_segment_type,
                )
                self.emit_segment_end()

            self.emit_segment_start(SegmentType.TEXT)

        self.emit_segment_content(text)
