import logging
from enum import Enum
from typing import Dict, Any, Optional, Type
from pydantic import BaseModel, Field, AwareDatetime, field_validator, ValidationInfo
import datetime
import uuid

from .stream_event_payloads import (
    StreamDataPayload,
    AssistantChunkData,
    AssistantCompleteResponseData,
    ToolInteractionLogEntryData,
    AgentStatusUpdateData,
    ErrorEventData,
    ToolApprovalRequestedData,
    ToolApprovedData,
    ToolDeniedData,
    ToolExecutionStartedData,
    ToolExecutionSucceededData,
    ToolExecutionFailedData,
    SegmentEventData,
    SystemTaskNotificationData,
    InterAgentMessageData,
    ToDoListUpdateData,
    ArtifactPersistedData,
    ArtifactUpdatedData,
)

logger = logging.getLogger(__name__)


class StreamEventType(str, Enum):
    ASSISTANT_CHUNK = "assistant_chunk"
    ASSISTANT_COMPLETE_RESPONSE = "assistant_complete_response"
    TOOL_INTERACTION_LOG_ENTRY = "tool_interaction_log_entry"
    AGENT_STATUS_UPDATED = "agent_status_updated"
    ERROR_EVENT = "error_event"
    TOOL_APPROVAL_REQUESTED = "tool_approval_requested"
    TOOL_APPROVED = "tool_approved"
    TOOL_DENIED = "tool_denied"
    TOOL_EXECUTION_STARTED = "tool_execution_started"
    TOOL_EXECUTION_SUCCEEDED = "tool_execution_succeeded"
    TOOL_EXECUTION_FAILED = "tool_execution_failed"
    SEGMENT_EVENT = "segment_event"
    SYSTEM_TASK_NOTIFICATION = "system_task_notification"
    INTER_AGENT_MESSAGE = "inter_agent_message"
    AGENT_TODO_LIST_UPDATE = "agent_todo_list_updated"
    ARTIFACT_PERSISTED = "artifact_persisted"
    ARTIFACT_UPDATED = "artifact_updated"


_STREAM_EVENT_TYPE_TO_PAYLOAD_CLASS: Dict[StreamEventType, Type[BaseModel]] = {
    StreamEventType.ASSISTANT_CHUNK: AssistantChunkData,
    StreamEventType.ASSISTANT_COMPLETE_RESPONSE: AssistantCompleteResponseData,
    StreamEventType.TOOL_INTERACTION_LOG_ENTRY: ToolInteractionLogEntryData,
    StreamEventType.AGENT_STATUS_UPDATED: AgentStatusUpdateData,
    StreamEventType.ERROR_EVENT: ErrorEventData,
    StreamEventType.TOOL_APPROVAL_REQUESTED: ToolApprovalRequestedData,
    StreamEventType.TOOL_APPROVED: ToolApprovedData,
    StreamEventType.TOOL_DENIED: ToolDeniedData,
    StreamEventType.TOOL_EXECUTION_STARTED: ToolExecutionStartedData,
    StreamEventType.TOOL_EXECUTION_SUCCEEDED: ToolExecutionSucceededData,
    StreamEventType.TOOL_EXECUTION_FAILED: ToolExecutionFailedData,
    StreamEventType.SEGMENT_EVENT: SegmentEventData,
    StreamEventType.SYSTEM_TASK_NOTIFICATION: SystemTaskNotificationData,
    StreamEventType.INTER_AGENT_MESSAGE: InterAgentMessageData,
    StreamEventType.AGENT_TODO_LIST_UPDATE: ToDoListUpdateData,
    StreamEventType.ARTIFACT_PERSISTED: ArtifactPersistedData,
    StreamEventType.ARTIFACT_UPDATED: ArtifactUpdatedData,
}


class StreamEvent(BaseModel):
    event_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Unique identifier for the event.",
    )
    timestamp: AwareDatetime = Field(
        default_factory=lambda: datetime.datetime.now(datetime.timezone.utc),
        description="Timestamp of when the event was created (UTC).",
    )
    event_type: StreamEventType = Field(
        ...,
        description="The type of the event. This acts as the discriminator.",
    )
    data: StreamDataPayload = Field(
        ...,
        description="Payload of the event, specific to the event_type.",
    )
    agent_id: Optional[str] = Field(
        default=None,
        description="Optional ID of the agent that originated this event.",
    )

    @field_validator("data", mode="before")
    def validate_data_based_on_event_type(cls, v, info: ValidationInfo):
        event_type_value = info.data.get("event_type")
        if not event_type_value:
            return v

        if isinstance(event_type_value, str):
            try:
                event_type = StreamEventType(event_type_value)
            except ValueError:  # pragma: no cover
                logger.error("Invalid event_type string '%s' for validation.", event_type_value)
                raise ValueError(f"Invalid event_type string '{event_type_value}'")
        elif isinstance(event_type_value, StreamEventType):
            event_type = event_type_value
        else:  # pragma: no cover
            logger.error(
                "event_type is of unexpected type %s during validation.",
                type(event_type_value),
            )
            raise TypeError(f"event_type is of unexpected type {type(event_type_value)}")

        payload_class = _STREAM_EVENT_TYPE_TO_PAYLOAD_CLASS.get(event_type)

        if payload_class:
            if isinstance(v, payload_class):
                return v
            if isinstance(v, dict):
                try:
                    return payload_class(**v)
                except Exception as exc:
                    logger.error(
                        "Failed to parse dict into %s for event_type %s: %s. Dict was: %s",
                        payload_class.__name__,
                        event_type.value,
                        exc,
                        v,
                    )
                    raise ValueError(
                        f"Data for event type {event_type.value} does not match expected model {payload_class.__name__}."
                    ) from exc
            logger.error(
                "Data for event type %s is of unexpected type %s. Expected dict or %s.",
                event_type.value,
                type(v),
                payload_class.__name__,
            )
            raise ValueError(
                f"Data for event type {event_type.value} is of unexpected type {type(v)}."
            )

        logger.warning("No specific payload class mapped for event_type: %s. Raw data: %s", event_type.value, v)
        if isinstance(v, dict):
            return v
        return v

    class Config:
        populate_by_name = True

    def __repr__(self) -> str:
        return (
            f"<StreamEvent event_id='{self.event_id}', agent_id='{self.agent_id}', "
            f"type='{self.event_type.value}', timestamp='{self.timestamp.isoformat()}', "
            f"data_type='{type(self.data).__name__}'>"
        )

    def __str__(self) -> str:
        return (
            f"StreamEvent[{self.event_type.value}] (ID: {self.event_id}, Agent: {self.agent_id or 'N/A'}): "
            f"Data: {self.data!r}"
        )
