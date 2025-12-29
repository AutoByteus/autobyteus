# file: autobyteus/tests/unit_tests/agent_team/streaming/test_agent_team_stream_events.py
import pytest
from pydantic import ValidationError

from autobyteus.agent.status.status_enum import AgentStatus
from autobyteus.agent_team.streaming.agent_team_stream_events import AgentTeamStreamEvent, AgentEventRebroadcastPayload, AgentTeamStatusTransitionData, SubTeamEventRebroadcastPayload
from autobyteus.agent_team.status import AgentTeamStatus
from autobyteus.agent.streaming.stream_events import StreamEvent, StreamEventType

def test_team_phase_transition_event_creation():
    """Tests successful creation of a TEAM-sourced event."""
    data = AgentTeamStatusTransitionData(
        new_status=AgentTeamStatus.IDLE,
        old_status=AgentTeamStatus.PROCESSING
    )
    event = AgentTeamStreamEvent(
        team_id="team-1",
        event_source_type="TEAM",
        data=data
    )
    assert isinstance(event.data, AgentTeamStatusTransitionData)
    assert event.data.new_status == AgentTeamStatus.IDLE

def test_agent_event_rebroadcast_event_creation():
    """Tests successful creation of an AGENT-sourced event."""
    mock_agent_event = StreamEvent(
        agent_id="agent-1",
        event_type=StreamEventType.AGENT_STATUS_TRANSITION,
        data={"new_status": AgentStatus.IDLE}
    )
    data = AgentEventRebroadcastPayload(
        agent_name="Coordinator",
        agent_event=mock_agent_event
    )
    event = AgentTeamStreamEvent(
        team_id="team-1",
        event_source_type="AGENT",
        data=data
    )
    assert isinstance(event.data, AgentEventRebroadcastPayload)
    assert event.data.agent_name == "Coordinator"
    assert event.data.agent_event.agent_id == "agent-1"

def test_sub_team_event_rebroadcast_event_creation():
    """Tests successful creation of a SUB_TEAM-sourced event."""
    mock_sub_team_event = AgentTeamStreamEvent(
        team_id="sub-team-2",
        event_source_type="TEAM",
        data=AgentTeamStatusTransitionData(new_status=AgentTeamStatus.IDLE)
    )
    data = SubTeamEventRebroadcastPayload(
        sub_team_node_name="ResearchTeam",
        sub_team_event=mock_sub_team_event
    )
    event = AgentTeamStreamEvent(
        team_id="team-1",
        event_source_type="SUB_TEAM",
        data=data
    )
    assert isinstance(event.data, SubTeamEventRebroadcastPayload)
    assert event.data.sub_team_node_name == "ResearchTeam"
    assert event.data.sub_team_event.team_id == "sub-team-2"


def test_validation_error_on_mismatched_data():
    """Tests that Pydantic raises an error for incorrect data shapes."""
    with pytest.raises(ValidationError):
        # TEAM source type expects AgentTeamStatusTransitionData, but we provide AGENT data
        AgentTeamStreamEvent(
            team_id="team-1",
            event_source_type="TEAM",
            data={"agent_name": "test", "agent_event": {}}
        )
    
    with pytest.raises(ValidationError):
        # AGENT source type expects AgentEventRebroadcastPayload, but we provide TEAM data
        AgentTeamStreamEvent(
            team_id="team-1",
            event_source_type="AGENT",
            data={"new_status": "idle"}
        )
    
    with pytest.raises(ValidationError):
        # SUB_TEAM source type expects SubTeamEventRebroadcastPayload, but we provide AGENT data
        AgentTeamStreamEvent(
            team_id="team-1",
            event_source_type="SUB_TEAM",
            data={"agent_name": "test", "agent_event": {}}
        )
