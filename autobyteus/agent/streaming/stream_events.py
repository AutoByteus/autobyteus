# file: autobyteus/autobyteus/agent/streaming/stream_events.py
import logging
from enum import Enum
from typing import Dict, Any, Optional 
from pydantic import BaseModel, Field, AwareDatetime 
import datetime
import uuid # For default event_id

logger = logging.getLogger(__name__)

class StreamEventType(str, Enum):
    """
    Defines the types of events that can appear in a unified agent output stream.
    """
    ASSISTANT_CHUNK = "assistant_chunk"
    ASSISTANT_FINAL_MESSAGE = "assistant_final_message"
    TOOL_INTERACTION_LOG_ENTRY = "tool_interaction_log_entry"
    AGENT_PHASE_UPDATE = "agent_phase_update" 
    ERROR_EVENT = "error_event" 
    TOOL_APPROVAL_REQUESTED = "tool_approval_requested" # Present


class StreamEvent(BaseModel):
    """
    Pydantic model for a unified, typed event in an agent's output stream.
    """
    event_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()), 
        description="Unique identifier for the event."
    )
    timestamp: AwareDatetime = Field(
        default_factory=lambda: datetime.datetime.now(datetime.timezone.utc),
        description="Timestamp of when the event was created (UTC)."
    )
    event_type: StreamEventType = Field(
        ..., 
        description="The type of the event."
    )
    data: Dict[str, Any] = Field(
        default_factory=dict, 
        description="Payload of the event, specific to the event_type."
    )
    agent_id: Optional[str] = Field(
        default=None, 
        description="Optional ID of the agent that originated this event."
    )

    class Config:
        populate_by_name = True 
        use_enum_values = True 

    def __repr__(self) -> str:
        return (f"<StreamEvent event_id='{self.event_id}', agent_id='{self.agent_id}', "
                f"type='{self.event_type.value}', timestamp='{self.timestamp.isoformat()}'>")

    def __str__(self) -> str:
        return (f"StreamEvent[{self.event_type.value}] (ID: {self.event_id}, Agent: {self.agent_id or 'N/A'}): "
                f"Data: {self.data}")

