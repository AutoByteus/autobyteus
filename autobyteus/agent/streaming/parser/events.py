"""
Event and Model definitions for the Streaming Parser.

Defines the "Message Part" hierarchy for data structure and the "Part Event" 
protocol for streaming wire transmission.
"""
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, Literal, Union
from pydantic import BaseModel, Field


# --- Data Models (The "Parts") ---

class MessagePart(BaseModel):
    """Base class for all message parts."""
    id: str
    type: str

class TextPart(MessagePart):
    """A part containing text content."""
    type: Literal["text"] = "text"
    content: str = ""

class ToolCallPart(MessagePart):
    """A part representing a tool call."""
    type: Literal["tool_call"] = "tool_call"
    tool_name: str
    arguments: Dict[str, Any] = Field(default_factory=dict)
    raw_arguments: str = ""  # The accumulated raw content (e.g. XML/JSON)

class ReasoningPart(MessagePart):
    """A part containing internal reasoning/thinking."""
    type: Literal["reasoning"] = "reasoning"
    content: str = ""


# --- Wire Protocol (The "Events") ---

class BasePartEvent(BaseModel):
    """Base class for streaming events."""
    part_id: str

class PartStartEvent(BasePartEvent):
    """Signal that a new part has started."""
    event: Literal["part_start"] = "part_start"
    part_type: Literal["text", "tool_call", "reasoning"]
    metadata: Dict[str, Any] = Field(default_factory=dict)

class PartDeltaEvent(BasePartEvent):
    """Signal a content chunk for the active part."""
    event: Literal["part_delta"] = "part_delta"
    delta: str

class PartEndEvent(BasePartEvent):
    """Signal that the part is finished."""
    event: Literal["part_end"] = "part_end"
    metadata: Dict[str, Any] = Field(default_factory=dict)  # Final/Additional data

# Union type for type hinting
PartEvent = Union[PartStartEvent, PartDeltaEvent, PartEndEvent]
