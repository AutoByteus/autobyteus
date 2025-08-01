# file: autobyteus/autobyteus/workflow/streaming/workflow_stream_events.py
import datetime
import uuid
from typing import Literal, Union
from pydantic import BaseModel, Field, model_validator

from .workflow_stream_event_payloads import WorkflowPhaseTransitionData, AgentEventRebroadcastPayload, SubWorkflowEventRebroadcastPayload

# A union of all possible payloads for a "WORKFLOW" sourced event.
WorkflowSpecificPayload = Union[WorkflowPhaseTransitionData]

# The top-level discriminated union for the main event stream's payload.
WorkflowStreamDataPayload = Union[WorkflowSpecificPayload, AgentEventRebroadcastPayload, SubWorkflowEventRebroadcastPayload]

class WorkflowStreamEvent(BaseModel):
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime.datetime = Field(default_factory=datetime.datetime.utcnow)
    workflow_id: str
    event_source_type: Literal["WORKFLOW", "AGENT", "SUB_WORKFLOW"]
    data: WorkflowStreamDataPayload

    @model_validator(mode='after')
    def check_data_matches_source_type(self) -> 'WorkflowStreamEvent':
        is_agent_event = self.event_source_type == "AGENT"
        is_agent_payload = isinstance(self.data, AgentEventRebroadcastPayload)

        is_sub_workflow_event = self.event_source_type == "SUB_WORKFLOW"
        is_sub_workflow_payload = isinstance(self.data, SubWorkflowEventRebroadcastPayload)

        is_workflow_event = self.event_source_type == "WORKFLOW"
        is_workflow_payload = isinstance(self.data, WorkflowPhaseTransitionData)

        if is_agent_event and not is_agent_payload:
            raise ValueError("event_source_type is 'AGENT' but data is not an AgentEventRebroadcastPayload")
        
        if is_sub_workflow_event and not is_sub_workflow_payload:
            raise ValueError("event_source_type is 'SUB_WORKFLOW' but data is not a SubWorkflowEventRebroadcastPayload")
        
        if is_workflow_event and not is_workflow_payload:
            raise ValueError("event_source_type is 'WORKFLOW' but data is not a valid workflow-specific payload")

        return self

# This is necessary for Pydantic v2 to correctly handle the recursive model
SubWorkflowEventRebroadcastPayload.model_rebuild()
