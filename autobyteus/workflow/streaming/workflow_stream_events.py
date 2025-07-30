# file: autobyteus/autobyteus/workflow/streaming/workflow_stream_events.py
import datetime
import uuid
from typing import Literal, Union
from pydantic import BaseModel, Field, model_validator

from .workflow_stream_event_payloads import WorkflowPhaseTransitionData, AgentEventRebroadcastPayload

# A union of all possible payloads for a "WORKFLOW" sourced event.
WorkflowSpecificPayload = Union[WorkflowPhaseTransitionData]

# The top-level discriminated union for the main event stream's payload.
WorkflowStreamDataPayload = Union[WorkflowSpecificPayload, AgentEventRebroadcastPayload]

class WorkflowStreamEvent(BaseModel):
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime.datetime = Field(default_factory=datetime.datetime.utcnow)
    workflow_id: str
    event_source_type: Literal["WORKFLOW", "AGENT"]
    data: WorkflowStreamDataPayload

    @model_validator(mode='after')
    def check_data_matches_source_type(self) -> 'WorkflowStreamEvent':
        """
        Ensures that the `data` payload type is consistent with the `event_source_type`.
        This enforces the logic of a discriminated union manually, as the discriminator
        field is on the parent model, not the payload models.
        """
        is_agent_event = self.event_source_type == "AGENT"
        is_agent_payload = isinstance(self.data, AgentEventRebroadcastPayload)

        is_workflow_event = self.event_source_type == "WORKFLOW"
        # Check against the actual members of the WorkflowSpecificPayload union
        is_workflow_payload = isinstance(self.data, WorkflowPhaseTransitionData)

        if is_agent_event and not is_agent_payload:
            raise ValueError("event_source_type is 'AGENT' but data is not an AgentEventRebroadcastPayload")
        
        if is_workflow_event and not is_workflow_payload:
            raise ValueError("event_source_type is 'WORKFLOW' but data is not a valid workflow-specific payload")

        return self
