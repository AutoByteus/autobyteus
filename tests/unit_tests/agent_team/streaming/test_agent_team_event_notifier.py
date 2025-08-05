# file: autobyteus/tests/unit_tests/agent_team/streaming/test_agent_team_event_notifier.py
import pytest
from unittest.mock import MagicMock, patch

from autobyteus.agent_team.streaming.agent_team_event_notifier import AgentTeamExternalEventNotifier
from autobyteus.agent_team.streaming.agent_team_stream_events import AgentTeamStreamEvent, AgentEventRebroadcastPayload, AgentTeamPhaseTransitionData, SubTeamEventRebroadcastPayload
from autobyteus.events.event_types import EventType
from autobyteus.agent_team.phases.agent_team_operational_phase import AgentTeamOperationalPhase
from autobyteus.agent.streaming.stream_events import StreamEvent, StreamEventType

@pytest.fixture
def notifier():
    mock_runtime = MagicMock()
    return AgentTeamExternalEventNotifier(team_id="team-123", runtime_ref=mock_runtime)

def test_notify_phase_change(notifier: AgentTeamExternalEventNotifier):
    """Tests that notify_phase_change creates and emits a correct TEAM event."""
    with patch.object(notifier, 'emit') as mock_emit:
        notifier.notify_phase_change(
            new_phase=AgentTeamOperationalPhase.IDLE,
            old_phase=AgentTeamOperationalPhase.BOOTSTRAPPING,
            extra_data={"error_message": "An error"}
        )
        
        mock_emit.assert_called_once_with(EventType.TEAM_STREAM_EVENT, payload=Anotfound)
        emitted_event = mock_emit.call_args.kwargs['payload']
        
        assert isinstance(emitted_event, AgentTeamStreamEvent)
        assert emitted_event.team_id == "team-123"
        assert emitted_event.event_source_type == "TEAM"
        
        data = emitted_event.data
        assert isinstance(data, AgentTeamPhaseTransitionData)
        assert data.new_phase == AgentTeamOperationalPhase.IDLE
        assert data.old_phase == AgentTeamOperationalPhase.BOOTSTRAPPING
        assert data.error_message == "An error"

def test_publish_agent_event(notifier: AgentTeamExternalEventNotifier):
    """Tests that publish_agent_event creates and emits a correct AGENT event."""
    agent_name = "Researcher"
    mock_agent_event_data = {"content": "chunk text", "is_complete": False}
    mock_agent_event = StreamEvent(
        agent_id="agent-abc", 
        event_type=StreamEventType.ASSISTANT_CHUNK, 
        data=mock_agent_event_data
    )

    with patch.object(notifier, 'emit') as mock_emit:
        notifier.publish_agent_event(agent_name, mock_agent_event)
        
        mock_emit.assert_called_once_with(EventType.TEAM_STREAM_EVENT, payload=Anotfound)
        emitted_event = mock_emit.call_args.kwargs['payload']
        
        assert isinstance(emitted_event, AgentTeamStreamEvent)
        assert emitted_event.team_id == "team-123"
        assert emitted_event.event_source_type == "AGENT"
        
        data = emitted_event.data
        assert isinstance(data, AgentEventRebroadcastPayload)
        assert data.agent_name == agent_name
        assert data.agent_event == mock_agent_event

def test_publish_sub_team_event(notifier: AgentTeamExternalEventNotifier):
    """Tests that publish_sub_team_event creates and emits a correct SUB_TEAM event."""
    sub_team_name = "ResearchTeam"
    mock_sub_team_event = AgentTeamStreamEvent(
        team_id="sub-team-456",
        event_source_type="TEAM",
        data=AgentTeamPhaseTransitionData(new_phase=AgentTeamOperationalPhase.IDLE)
    )

    with patch.object(notifier, 'emit') as mock_emit:
        notifier.publish_sub_team_event(sub_team_name, mock_sub_team_event)

        mock_emit.assert_called_once_with(EventType.TEAM_STREAM_EVENT, payload=Anotfound)
        emitted_event = mock_emit.call_args.kwargs['payload']

        assert isinstance(emitted_event, AgentTeamStreamEvent)
        assert emitted_event.team_id == "team-123"
        assert emitted_event.event_source_type == "SUB_TEAM"

        data = emitted_event.data
        assert isinstance(data, SubTeamEventRebroadcastPayload)
        assert data.sub_team_node_name == sub_team_name
        assert data.sub_team_event == mock_sub_team_event
