# file: autobyteus/autobyteus/agent/streaming/stream_events.py
import logging
from enum import Enum
from typing import Dict, Any, Optional, Union, Type 
from pydantic import BaseModel, Field, AwareDatetime, validator, RootModel 
import datetime
import uuid 

# Import the payload models
from .stream_event_payloads import (
    StreamDataPayload, 
    AssistantChunkData,
    AssistantCompleteResponseData, # UPDATED import
    ToolInteractionLogEntryData,
    AgentOperationalPhaseTransitionData, 
    ErrorEventData,
    ToolInvocationApprovalRequestedData,
    EmptyData
)

logger = logging.getLogger(__name__)

class StreamEventType(str, Enum):
    """
    Defines the types of events that can appear in a unified agent output stream
    provided by AgentEventStream.
    """
    ASSISTANT_CHUNK = "assistant_chunk"
    ASSISTANT_COMPLETE_RESPONSE = "assistant_complete_response" # RENAMED from ASSISTANT_FINAL_MESSAGE
    TOOL_INTERACTION_LOG_ENTRY = "tool_interaction_log_entry"
    AGENT_OPERATIONAL_PHASE_TRANSITION = "agent_operational_phase_transition" # RENAMED from AGENT_PHASE_UPDATE
    ERROR_EVENT = "error_event" 
    TOOL_INVOCATION_APPROVAL_REQUESTED = "tool_invocation_approval_requested" 
    AGENT_IDLE = "agent_idle" # ADDED: New event type for when agent becomes idle.


_STREAM_EVENT_TYPE_TO_PAYLOAD_CLASS: Dict[StreamEventType, Type[BaseModel]] = {
    StreamEventType.ASSISTANT_CHUNK: AssistantChunkData,
    StreamEventType.ASSISTANT_COMPLETE_RESPONSE: AssistantCompleteResponseData, # UPDATED mapping
    StreamEventType.TOOL_INTERACTION_LOG_ENTRY: ToolInteractionLogEntryData,
    StreamEventType.AGENT_OPERATIONAL_PHASE_TRANSITION: AgentOperationalPhaseTransitionData, # RENAMED mapping
    StreamEventType.ERROR_EVENT: ErrorEventData,
    StreamEventType.TOOL_INVOCATION_APPROVAL_REQUESTED: ToolInvocationApprovalRequestedData,
    StreamEventType.AGENT_IDLE: AgentOperationalPhaseTransitionData, # ADDED: Mapped to the same payload as phase update
}


class StreamEvent(BaseModel):
    """
    Pydantic model for a unified, typed event in an agent's output stream.
    The 'data' field is now a discriminated union of specific payload models
    based on 'event_type'.
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
        description="The type of the event. This acts as the discriminator."
    )
    data: StreamDataPayload = Field( 
        ..., 
        description="Payload of the event, specific to the event_type."
    )
    agent_id: Optional[str] = Field(
        default=None, 
        description="Optional ID of the agent that originated this event."
    )

    @validator('data', pre=True, always=True)
    def validate_data_based_on_event_type(cls, v, values, **kwargs):
        event_type_value = values.get('event_type')
        if not event_type_value: 
            return v 

        if isinstance(event_type_value, str):
            try:
                event_type = StreamEventType(event_type_value)
            except ValueError: # pragma: no cover
                logger.error(f"Invalid event_type string '{event_type_value}' for validation.")
                raise ValueError(f"Invalid event_type string '{event_type_value}'")
        elif isinstance(event_type_value, StreamEventType):
            event_type = event_type_value
        else: # pragma: no cover
            logger.error(f"event_type is of unexpected type {type(event_type_value)} during validation.")
            raise TypeError(f"event_type is of unexpected type {type(event_type_value)}")


        payload_class = _STREAM_EVENT_TYPE_TO_PAYLOAD_CLASS.get(event_type)
        
        if payload_class:
            if isinstance(v, payload_class): 
                return v
            if isinstance(v, dict):
                try:
                    return payload_class(**v)
                except Exception as e:
                    logger.error(f"Failed to parse dict into {payload_class.__name__} for event_type {event_type.value}: {e}. Dict was: {v}")
                    raise ValueError(f"Data for event type {event_type.value} does not match expected model {payload_class.__name__}.") from e
            logger.error(f"Data for event type {event_type.value} is of unexpected type {type(v)}. Expected dict or {payload_class.__name__}.")
            raise ValueError(f"Data for event type {event_type.value} is of unexpected type {type(v)}.")
        
        logger.warning(f"No specific payload class mapped for event_type: {event_type.value}. Raw data: {v}")
        if isinstance(v, dict): 
            return v
        return v


    class Config:
        populate_by_name = True 

    def __repr__(self) -> str:
        return (f"<StreamEvent event_id='{self.event_id}', agent_id='{self.agent_id}', "
                f"type='{self.event_type.value}', timestamp='{self.timestamp.isoformat()}', data_type='{type(self.data).__name__}'>")

    def __str__(self) -> str:
        return (f"StreamEvent[{self.event_type.value}] (ID: {self.event_id}, Agent: {self.agent_id or 'N/A'}): "
                f"Data: {self.data!r}")
