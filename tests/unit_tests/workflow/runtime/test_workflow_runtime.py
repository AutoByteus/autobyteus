# file: autobyteus/tests/unit_tests/workflow/runtime/test_workflow_runtime.py
import asyncio
import pytest
from unittest.mock import MagicMock, AsyncMock, patch

from autobyteus.workflow.runtime.workflow_runtime import WorkflowRuntime
from autobyteus.workflow.events.workflow_events import ProcessUserMessageEvent

@pytest.mark.asyncio
@patch('autobyteus.workflow.runtime.workflow_runtime.WorkflowWorker')
async def test_submit_event_enqueues_correctly(MockWorker, workflow_context):
    """Tests that submit_event routes different events to the correct queue."""
    mock_worker_instance = MockWorker.return_value
    # Mock the schedule_coroutine to immediately run the coro
    async def run_coro_immediately(coro_factory):
        await coro_factory()
        return MagicMock() # Return a mock future
    mock_worker_instance.schedule_coroutine.side_effect = run_coro_immediately

    registry = MagicMock()
    runtime = WorkflowRuntime(workflow_context, registry)
    
    # Test ProcessUserMessageEvent
    user_message_event = ProcessUserMessageEvent(user_message=MagicMock(), target_agent_name="test")
    await runtime.submit_event(user_message_event)
    
    queue_manager = workflow_context.state.input_event_queues
    queue_manager.enqueue_user_message.assert_awaited_once_with(user_message_event)
    queue_manager.enqueue_internal_system_event.assert_not_awaited()

    # Test other event
    queue_manager.reset_mock()
    other_event = MagicMock()
    await runtime.submit_event(other_event)
    queue_manager.enqueue_user_message.assert_not_awaited()
    queue_manager.enqueue_internal_system_event.assert_awaited_once_with(other_event)
