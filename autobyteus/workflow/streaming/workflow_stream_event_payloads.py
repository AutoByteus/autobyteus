# file: autobyteus/autobyteus/workflow/streaming/workflow_stream_event_payloads.py
from typing import Optional, Any
from pydantic import BaseModel

from autobyteus.workflow.phases.workflow_operational_phase import WorkflowOperationalPhase
from autobyteus.agent.streaming.stream_events import StreamEvent

class BaseWorkflowStreamPayload(BaseModel):
    pass

class WorkflowPhaseTransitionData(BaseWorkflowStreamPayload):
    new_phase: WorkflowOperationalPhase
    old_phase: Optional[WorkflowOperationalPhase] = None
    error_message: Optional[str] = None

class AgentActivityLogData(BaseWorkflowStreamPayload):
    """
    Represents a log of activity from a member agent within the workflow.
    This can be a simple status update or a rebroadcast of a complex event.
    """
    agent_name: str
    activity: str
    details: Optional[Any] = None

class WorkflowFinalResultData(BaseWorkflowStreamPayload):
    result: Any
