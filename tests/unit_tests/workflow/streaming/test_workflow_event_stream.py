import asyncio
import pytest
from unittest.mock import MagicMock, create_autospec

from autobyteus.workflow.streaming.workflow_event_stream import WorkflowEventStream
from autobyteus.workflow.streaming.workflow_stream_events import WorkflowStreamEvent
from autobyteus.events.event_types import EventType
from autobyteus.workflow.agentic_workflow import AgenticWorkflow
from autobyteus.workflow.status import WorkflowStatus
from autobyteus.agent.streaming.stream_events import StreamEventType

pytestmark = pytest.mark.asyncio

@pytest.fixture
def mock_workflow():
    # The original MagicMock with `spec` does not correctly handle instance attributes
    # like `_runtime` that are defined in `__init__`. This causes an AttributeError
    # when the test tries to access `workflow._runtime`.
    #
    # The fix is to use `create_autospec`, which is more powerful. We can tell it
    # to create the mock with the necessary attributes already configured.
    
    # 1. Create a mock for the nested `_runtime` attribute.
    mock_runtime_obj = MagicMock()
    # The notifier needs `subscribe`, `unsubscribe`, and `emit` methods.
    mock_runtime_obj.notifier = MagicMock(name="notifier_mock")
    mock_runtime_obj.notifier.subscribe = MagicMock(name="subscribe_mock")
    mock_runtime_obj.notifier.emit = MagicMock(name="emit_mock")
    mock_runtime_obj.notifier.unsubscribe = MagicMock(name="unsubscribe_mock")


    # 2. Create the main mock, configuring it with the attributes needed by the test.
    workflow = create_autospec(
        AgenticWorkflow,
        instance=True,
        workflow_id="wf-stream-test",
        _runtime=mock_runtime_obj,
    )
    return workflow

@pytest.fixture
def stream(mock_workflow):
    # Create the stream, which will call `subscribe` on the mock notifier.
    s = WorkflowEventStream(mock_workflow)

    # --- FIX for AssertionError ---
    # A standard MagicMock is passive. It records calls to `subscribe` and `emit`
    # but doesn't link them. We need to actively call the subscribed handler when
    # `emit` is called to simulate a real event emitter.
    
    # 1. Capture the handler that was just subscribed by the WorkflowEventStream.
    # The handler is the second positional argument to `subscribe`.
    subscribe_args, _ = mock_workflow._runtime.notifier.subscribe.call_args
    subscribed_handler = subscribe_args[1]

    # 2. Define a side effect function for the `emit` method.
    def emit_side_effect(event_type, payload):
        # This simulates the emitter invoking the handler if the event type matches.
        if event_type == EventType.WORKFLOW_STREAM_EVENT:
            subscribed_handler(payload=payload)

    # 3. Assign this active behavior to the mock's `emit` method.
    mock_workflow._runtime.notifier.emit.side_effect = emit_side_effect
    
    yield s
    
    # Teardown
    asyncio.run(s.close())

async def test_stream_initialization(mock_workflow):
    """Tests that the stream subscribes to the correct event upon creation."""
    stream = WorkflowEventStream(mock_workflow)
    mock_workflow._runtime.notifier.subscribe.assert_called_once_with(
        EventType.WORKFLOW_STREAM_EVENT, stream._handle_event
    )

async def test_handle_event_queues_correct_event(stream: WorkflowEventStream):
    """Tests that the handler correctly filters and queues events for its workflow."""
    correct_event = WorkflowStreamEvent(workflow_id=stream.workflow_id, event_source_type="WORKFLOW", data={"new_status": WorkflowStatus.IDLE})
    wrong_event = WorkflowStreamEvent(workflow_id="some-other-wf", event_source_type="WORKFLOW", data={"new_status": WorkflowStatus.IDLE})
    
    stream._handle_event(payload=correct_event)
    stream._handle_event(payload=wrong_event)
    
    assert stream._internal_q.qsize() == 1
    assert stream._internal_q.get() is correct_event

async def test_all_events_stream_and_close(stream: WorkflowEventStream, mock_workflow):
    """Tests the full lifecycle: streaming events and closing gracefully."""
    # FIX: Corrected the data payloads to be valid for their respective Pydantic models.
    # Using the enum member for `new_status` is more robust than a raw string.
    event1 = WorkflowStreamEvent(
        workflow_id=stream.workflow_id,
        event_source_type="WORKFLOW",
        data={"new_status": WorkflowStatus.IDLE}
    )
    # FIX: The `agent_event` payload was an empty dict `{}`, which is not a valid AgentStreamEvent.
    # Provided a minimal, valid nested structure to satisfy Pydantic's validation.
    event2 = WorkflowStreamEvent(
        workflow_id=stream.workflow_id,
        event_source_type="AGENT",
        data={
            "agent_name": "a",
            "agent_event": {
                "event_type": StreamEventType.ASSISTANT_CHUNK,
                "data": {"content": "test", "is_complete": False}
            }
        }
    )
    
    # Simulate events coming from the notifier
    async def produce_events():
        await asyncio.sleep(0.01)
        # The mock is now nested correctly under _runtime
        mock_workflow._runtime.notifier.emit(EventType.WORKFLOW_STREAM_EVENT, payload=event1)
        await asyncio.sleep(0.01)
        mock_workflow._runtime.notifier.emit(EventType.WORKFLOW_STREAM_EVENT, payload=event2)
        await asyncio.sleep(0.01)
        await stream.close()

    producer_task = asyncio.create_task(produce_events())

    results = [event async for event in stream.all_events()]
    
    await producer_task

    assert results == [event1, event2]
    # The mock is now nested correctly under _runtime
    mock_workflow._runtime.notifier.unsubscribe.assert_called_once_with(EventType.WORKFLOW_STREAM_EVENT, stream._handle_event)
