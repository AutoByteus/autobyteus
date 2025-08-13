# file: autobyteus/autobyteus/agent_team/streaming/agent_team_event_notifier.py
import logging
from typing import Optional, Dict, Any, TYPE_CHECKING

from autobyteus.events.event_emitter import EventEmitter
from autobyteus.events.event_types import EventType
from autobyteus.agent_team.phases.agent_team_operational_phase import AgentTeamOperationalPhase
from autobyteus.agent.streaming.stream_events import StreamEvent as AgentStreamEvent
from .agent_team_stream_events import AgentTeamStreamEvent, AgentEventRebroadcastPayload, AgentTeamPhaseTransitionData, SubTeamEventRebroadcastPayload
from autobyteus.task_management.events import BaseTaskBoardEvent

if TYPE_CHECKING:
    from autobyteus.agent_team.runtime.agent_team_runtime import AgentTeamRuntime
    from autobyteus.agent_team.streaming.agent_team_stream_events import AgentTeamStreamEvent as AgentTeamStreamEventTypeHint

logger = logging.getLogger(__name__)

class AgentTeamExternalEventNotifier(EventEmitter):
    """
    Responsible for emitting unified AgentTeamStreamEvents for consumption by
    external listeners (like a UI or the AgentTeamEventStream).
    """
    def __init__(self, team_id: str, runtime_ref: 'AgentTeamRuntime'):
        super().__init__()
        self.team_id = team_id
        self.runtime_ref = runtime_ref
        logger.debug(f"AgentTeamExternalEventNotifier initialized for team '{self.team_id}'.")

    def _emit_event(self, event: 'AgentTeamStreamEventTypeHint'):
        """
        Emits a fully-formed AgentTeamStreamEvent.
        """
        self.emit(EventType.TEAM_STREAM_EVENT, payload=event)

    def notify_phase_change(self, new_phase: AgentTeamOperationalPhase, old_phase: Optional[AgentTeamOperationalPhase], extra_data: Optional[Dict[str, Any]] = None):
        """
        Notifies of an agent team phase transition by creating and emitting a
        'TEAM' sourced event.
        """
        payload_dict = { "new_phase": new_phase, "old_phase": old_phase, "error_message": extra_data.get("error_message") if extra_data else None }
        filtered_payload_dict = {k: v for k, v in payload_dict.items() if v is not None}
        event = AgentTeamStreamEvent(team_id=self.team_id, event_source_type="TEAM", data=AgentTeamPhaseTransitionData(**filtered_payload_dict))
        self._emit_event(event)
    
    def publish_agent_event(self, agent_name: str, agent_event: AgentStreamEvent):
        """
        Wraps an event from a direct member agent and publishes it on the main team stream.
        """
        event = AgentTeamStreamEvent(team_id=self.team_id, event_source_type="AGENT", data=AgentEventRebroadcastPayload(agent_name=agent_name, agent_event=agent_event))
        self._emit_event(event)
        
    def publish_sub_team_event(self, sub_team_node_name: str, sub_team_event: 'AgentTeamStreamEventTypeHint'):
        """
        Wraps an event from a sub-team and publishes it on the parent team stream.
        """
        event = AgentTeamStreamEvent(team_id=self.team_id, event_source_type="SUB_TEAM", data=SubTeamEventRebroadcastPayload(sub_team_node_name=sub_team_node_name, sub_team_event=sub_team_event))
        self._emit_event(event)

    def handle_and_publish_task_board_event(self, payload: BaseTaskBoardEvent, **kwargs):
        """
        Listener for TaskBoard events. It wraps the event and publishes it on the main team stream.
        """
        event = AgentTeamStreamEvent(team_id=self.team_id, event_source_type="TASK_BOARD", data=payload)
        self._emit_event(event)
