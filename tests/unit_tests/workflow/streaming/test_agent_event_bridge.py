# file: autobyteus/tests/unit_tests/workflow/streaming/test_agent_event_bridge.py
import asyncio
import pytest
import pytest_asyncio
from unittest.mock import MagicMock, AsyncMock, patch

from autobyteus.workflow.streaming.agent_event_bridge import AgentEventBridge
from autobyteus.agent.streaming.agent_event_stream import AgentEventStream
from autobyteus.workflow.streaming.workflow_event_notifier import WorkflowExternalEventNotifier
from autobyteus.agent.streaming.stream_events import StreamEvent, StreamEventType
from autobyteus.agent.agent import Agent
from autobyteus.agent.phases import AgentOperationalPhase

pytestmark = pytest.mark.asyncio

@pytest.fixture
def mock_agent_event_stream():
    stream = MagicMock(spec=AgentEventStream)
    # Use an actual asyncio.Queue to allow the bridge's background task to interact with it
    event_queue = asyncio.Queue()
    async def all_events_iterator():
        while True:
            try:
                event = await event_queue.get()
                if event is None: # Sentinel for stopping
                    break
                yield event
            except asyncio.CancelledError:
                break
    stream.all_events.return_value = all_events_iterator()
    stream.close = AsyncMock()
    # Attach the queue for the test to use
    stream.event_queue = event_queue
    return stream

@pytest.fixture
def mock_notifier():
    return MagicMock(spec=WorkflowExternalEventNotifier)

@pytest_asyncio.fixture
async def bridge(mock_agent_event_stream, mock_notifier):
    # FIX: Use @pytest_asyncio.fixture for fixtures defined with `async def`.
    # The standard @pytest.fixture does not correctly handle the lifecycle
    # (setup, yield, teardown) of an async generator fixture.
    with patch('autobyteus.workflow.streaming.agent_event_bridge.AgentEventStream', return_value=mock_agent_event_stream):
        loop = asyncio.get_running_loop()
        b = AgentEventBridge(agent=MagicMock(spec=Agent), agent_name="TestAgent", notifier=mock_notifier, loop=loop)
        yield b
        # Teardown: ensure the bridge is cancelled
        await b.cancel()

async def test_bridge_forwards_events(bridge: AgentEventBridge, mock_agent_event_stream, mock_notifier):
    """
    Tests that the bridge correctly consumes events from the stream and forwards them to the notifier.
    This is the core logic that was previously tested inside test_team_manager.py.
    """
    # FIX: Provide valid data payloads for the Pydantic models.
    # An empty dictionary `{}` is not valid for these event types.
    event1 = StreamEvent(
        agent_id="a1",
        event_type=StreamEventType.ASSISTANT_CHUNK,
        data={"content": "chunk text", "is_complete": False} # Valid AssistantChunkData
    )
    event2 = StreamEvent(
        agent_id="a1",
        event_type=StreamEventType.AGENT_IDLE,
        data={"new_phase": AgentOperationalPhase.IDLE} # Valid AgentOperationalPhaseTransitionData
    )

    # Put events onto the stream's queue
    await mock_agent_event_stream.event_queue.put(event1)
    await mock_agent_event_stream.event_queue.put(event2)
    
    # Give the bridge's background task time to process the events
    await asyncio.sleep(0.05)

    # Verify the notifier was called for each event
    assert mock_notifier.publish_agent_event.call_count == 2
    mock_notifier.publish_agent_event.assert_any_call("TestAgent", event1)
    mock_notifier.publish_agent_event.assert_any_call("TestAgent", event2)

async def test_bridge_cancel_stops_task_and_closes_stream(bridge: AgentEventBridge, mock_agent_event_stream):
    """
    Tests that cancelling the bridge stops its background task and cleans up the stream.
    """
    # Let the task run for a moment
    await asyncio.sleep(0.01)
    assert not bridge._task.done()

    await bridge.cancel()

    assert bridge._task.done()
    mock_agent_event_stream.close.assert_awaited_once()
