# file: autobyteus/autobyteus/agent/workflow/streaming/workflow_stream_events.py
import datetime
import uuid
from enum import Enum
from typing import Optional, Union, Dict, Type
from pydantic import BaseModel, Field, field_validator, ValidationInfo

from .workflow_stream_event_payloads import (
    WorkflowPhaseTransitionData,
    AgentActivityLogData,
    WorkflowFinalResultData,
)

class WorkflowStreamEventType(str, Enum):
    """Defines event types for the workflow's external event stream."""
    WORKFLOW_PHASE_TRANSITION = "workflow_phase_transition"
    AGENT_ACTIVITY_LOG = "agent_activity_log"
    WORKFLOW_FINAL_RESULT = "workflow_final_result"

WorkflowStreamDataPayload = Union[
    WorkflowPhaseTransitionData,
    AgentActivityLogData,
    WorkflowFinalResultData,
]

_WORKFLOW_EVENT_TYPE_TO_PAYLOAD_CLASS: Dict[WorkflowStreamEventType, Type[BaseModel]] = {
    WorkflowStreamEventType.WORKFLOW_PHASE_TRANSITION: WorkflowPhaseTransitionData,
    WorkflowStreamEventType.AGENT_ACTIVITY_LOG: AgentActivityLogData,
    WorkflowStreamEventType.WORKFLOW_FINAL_RESULT: WorkflowFinalResultData,
}

class WorkflowStreamEvent(BaseModel):
    """Pydantic model for a unified, typed event in a workflow's output stream."""
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime.datetime = Field(default_factory=datetime.datetime.utcnow)
    event_type: WorkflowStreamEventType
    data: WorkflowStreamDataPayload
    workflow_id: str

    @field_validator('data', mode='before')
    def validate_data(cls, v, info: ValidationInfo):
        event_type = info.data.get('event_type')
        if event_type:
            payload_class = _WORKFLOW_EVENT_TYPE_TO_PAYLOAD_CLASS.get(event_type)
            if payload_class and isinstance(v, dict):
                return payload_class(**v)
        return v
