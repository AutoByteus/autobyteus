# file: autobyteus/autobyteus/agent_team/streaming/agent_team_stream_event_payloads.py
from typing import Optional, Any
from pydantic import BaseModel, Field
from autobyteus.agent_team.phases.agent_team_operational_phase import AgentTeamOperationalPhase
from autobyteus.agent.streaming.stream_events import StreamEvent as AgentStreamEvent
from autobyteus.task_management.events import TasksAddedEvent, TaskStatusUpdatedEvent
# Need to use a forward reference string to avoid circular import at runtime
from typing import TYPE_CHECKING, Union
if TYPE_CHECKING:
    from autobyteus.agent_team.streaming.agent_team_stream_events import AgentTeamStreamEvent

# --- Payloads for events originating from the "TEAM" source ---
class BaseTeamSpecificPayload(BaseModel):
    pass

class AgentTeamPhaseTransitionData(BaseTeamSpecificPayload):
    new_phase: AgentTeamOperationalPhase
    old_phase: Optional[AgentTeamOperationalPhase] = None
    error_message: Optional[str] = None

# --- Payload for events originating from the "AGENT" source ---
class AgentEventRebroadcastPayload(BaseModel):
    agent_name: str # The friendly name, e.g., "Researcher_1"
    agent_event: AgentStreamEvent # The original, unmodified event from the agent

# --- Payload for events originating from the "SUB_TEAM" source ---
class SubTeamEventRebroadcastPayload(BaseModel):
    sub_team_node_name: str # The friendly name of the sub-team node
    sub_team_event: "AgentTeamStreamEvent" = Field(..., description="The original, unmodified event from the sub-team's stream")

# --- Payload for events originating from the "TASK_BOARD" source ---
TaskBoardEventPayload = Union[TasksAddedEvent, TaskStatusUpdatedEvent]
