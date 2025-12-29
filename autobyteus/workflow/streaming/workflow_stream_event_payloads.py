# file: autobyteus/autobyteus/workflow/streaming/workflow_stream_event_payloads.py
from typing import Optional, Any
from pydantic import BaseModel, Field
from autobyteus.workflow.status.workflow_status import WorkflowStatus
from autobyteus.agent.streaming.stream_events import StreamEvent as AgentStreamEvent
# Need to use a forward reference string to avoid circular import at runtime
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from autobyteus.workflow.streaming.workflow_stream_events import WorkflowStreamEvent

# --- Payloads for events originating from the "WORKFLOW" source ---
class BaseWorkflowSpecificPayload(BaseModel):
    pass

class WorkflowStatusUpdateData(BaseWorkflowSpecificPayload):
    new_status: WorkflowStatus
    old_status: Optional[WorkflowStatus] = None
    error_message: Optional[str] = None

# --- Payload for events originating from the "AGENT" source ---
class AgentEventRebroadcastPayload(BaseModel):
    agent_name: str # The friendly name, e.g., "Researcher_1"
    agent_event: AgentStreamEvent # The original, unmodified event from the agent

# --- Payload for events originating from the "SUB_WORKFLOW" source ---
class SubWorkflowEventRebroadcastPayload(BaseModel):
    sub_workflow_node_name: str # The friendly name of the sub-workflow node
    sub_workflow_event: "WorkflowStreamEvent" = Field(..., description="The original, unmodified event from the sub-workflow's stream")
