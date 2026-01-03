"""
Segment Event definitions for the Streaming Parser.

These dataclasses define the structured events that the parser emits
as it incrementally parses LLM response chunks.
"""
from dataclasses import dataclass, field
from typing import Dict, Any, Optional
from enum import Enum


class SegmentType(str, Enum):
    """Types of content segments that can be parsed from LLM responses."""
    TEXT = "text"
    TOOL_CALL = "tool_call"
    WRITE_FILE = "write_file"
    RUN_TERMINAL_CMD = "run_terminal_cmd"
    IFRAME = "iframe"
    REASONING = "reasoning"


class SegmentEventType(str, Enum):
    """Types of segment lifecycle events."""
    START = "SEGMENT_START"
    CONTENT = "SEGMENT_CONTENT"
    END = "SEGMENT_END"


@dataclass
class SegmentEvent:
    """
    A structured event emitted by the streaming parser.
    
    Attributes:
        event_type: The lifecycle stage of this event (START, CONTENT, END).
        segment_id: Unique identifier for the segment this event belongs to.
        segment_type: The type of content segment (only present in START events).
        payload: Additional data for the event (e.g., delta content, metadata).
    """
    event_type: SegmentEventType
    segment_id: str
    segment_type: Optional[SegmentType] = None
    payload: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize the event to a dictionary for JSON transmission."""
        result = {
            "type": self.event_type.value,
            "segment_id": self.segment_id,
            "payload": self.payload
        }
        if self.segment_type is not None:
            result["segment_type"] = self.segment_type.value
        return result

    @classmethod
    def start(cls, segment_id: str, segment_type: SegmentType, **metadata) -> "SegmentEvent":
        """Factory method to create a SEGMENT_START event."""
        return cls(
            event_type=SegmentEventType.START,
            segment_id=segment_id,
            segment_type=segment_type,
            payload={"metadata": metadata} if metadata else {}
        )

    @classmethod
    def content(cls, segment_id: str, delta: Any) -> "SegmentEvent":
        """Factory method to create a SEGMENT_CONTENT event."""
        return cls(
            event_type=SegmentEventType.CONTENT,
            segment_id=segment_id,
            payload={"delta": delta}
        )

    @classmethod
    def end(cls, segment_id: str) -> "SegmentEvent":
        """Factory method to create a SEGMENT_END event."""
        return cls(
            event_type=SegmentEventType.END,
            segment_id=segment_id
        )
