# file: autobyteus/tests/unit_tests/agent_team/streaming/test_agent_team_event_stream.py
import asyncio
import pytest
from unittest.mock import MagicMock, create_autospec

from autobyteus.agent_team.streaming.agent_team_event_stream import AgentTeamEventStream
from autobyteus.agent_team.streaming.agent_team_stream_events import AgentTeamStreamEvent
from autobyteus.events.event_types import EventType
from autobyteus.agent_team.agent_team import AgentTeam
from autobyteus.agent_team.phases import AgentTeamOperationalPhase
from autobyteus.agent.streaming.stream_events import StreamEventType

pytestmark = pytest.mark.asyncio

@pytest.fixture
def mock_team():
    mock_runtime_obj = MagicMock()
    mock_runtime_obj.notifier = MagicMock(name="notifier_mock")
    mock_runtime_obj.notifier.subscribe = MagicMock(name="subscribe_mock")
    mock_runtime_obj.notifier.emit = MagicMock(name="emit_mock")
    mock_runtime_obj.notifier.unsubscribe = MagicMock(name="unsubscribe_mock")

    team = create_autospec(
        AgentTeam,
        instance=True,
        team_id="team-stream-test",
        _runtime=mock_runtime_obj,
    )
    return team

@pytest.fixture
def stream(mock_team):
    s = AgentTeamEventStream(mock_team)
    
    subscribe_args, _ = mock_team._runtime.notifier.subscribe.call_args
    subscribed_handler = subscribe_args[1]

    def emit_side_effect(event_type, payload):
        if event_type == EventType.TEAM_STREAM_EVENT:
            subscribed_handler(payload=payload)

    mock_team._runtime.notifier.emit.side_effect = emit_side_effect
    
    yield s
    
    asyncio.run(s.close())

async def test_stream_initialization(mock_team):
    """Tests that the stream subscribes to the correct event upon creation."""
    stream = AgentTeamEventStream(mock_team)
    mock_team._runtime.notifier.subscribe.assert_called_once_with(
        EventType.TEAM_STREAM_EVENT, stream._handle_event
    )

async def test_handle_event_queues_correct_event(stream: AgentTeamEventStream):
    """Tests that the handler correctly filters and queues events for its team."""
    correct_event = AgentTeamStreamEvent(team_id=stream.team_id, event_source_type="TEAM", data={"new_phase": AgentTeamOperationalPhase.IDLE})
    wrong_event = AgentTeamStreamEvent(team_id="some-other-team", event_source_type="TEAM", data={"new_phase": AgentTeamOperationalPhase.IDLE})
    
    stream._handle_event(payload=correct_event)
    stream._handle_event(payload=wrong_event)
    
    assert stream._internal_q.qsize() == 1
    assert stream._internal_q.get() is correct_event

async def test_all_events_stream_and_close(stream: AgentTeamEventStream, mock_team):
    """Tests the full lifecycle: streaming events and closing gracefully."""
    event1 = AgentTeamStreamEvent(
        team_id=stream.team_id,
        event_source_type="TEAM",
        data={"new_phase": AgentTeamOperationalPhase.IDLE}
    )
    event2 = AgentTeamStreamEvent(
        team_id=stream.team_id,
        event_source_type="AGENT",
        data={
            "agent_name": "a",
            "agent_event": {
                "event_type": StreamEventType.ASSISTANT_CHUNK,
                "data": {"content": "test", "is_complete": False}
            }
        }
    )
    
    async def produce_events():
        await asyncio.sleep(0.01)
        mock_team._runtime.notifier.emit(EventType.TEAM_STREAM_EVENT, payload=event1)
        await asyncio.sleep(0.01)
        mock_team._runtime.notifier.emit(EventType.TEAM_STREAM_EVENT, payload=event2)
        await asyncio.sleep(0.01)
        await stream.close()

    producer_task = asyncio.create_task(produce_events())

    results = [event async for event in stream.all_events()]
    
    await producer_task

    assert results == [event1, event2]
    mock_team._runtime.notifier.unsubscribe.assert_called_once_with(EventType.TEAM_STREAM_EVENT, stream._handle_event)
