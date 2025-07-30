# file: autobyteus/autobyteus/workflow/streaming/workflow_stream_event_payloads.py
from typing import Optional, Any
from pydantic import BaseModel
from autobyteus.workflow.phases.workflow_operational_phase import WorkflowOperationalPhase
from autobyteus.agent.streaming.stream_events import StreamEvent as AgentStreamEvent

# --- Payloads for events originating from the "WORKFLOW" source ---
class BaseWorkflowSpecificPayload(BaseModel):
    pass

class WorkflowPhaseTransitionData(BaseWorkflowSpecificPayload):
    new_phase: WorkflowOperationalPhase
    old_phase: Optional[WorkflowOperationalPhase] = None
    error_message: Optional[str] = None

# --- Payload for events originating from the "AGENT" source ---
class AgentEventRebroadcastPayload(BaseModel):
    agent_name: str # The friendly name, e.g., "Researcher_1"
    agent_event: AgentStreamEvent # The original, unmodified event from the agent
