# file: autobyteus/tests/unit_tests/agent_team/runtime/test_agent_team_runtime.py
import asyncio
import pytest
from unittest.mock import MagicMock, AsyncMock, patch

from autobyteus.agent_team.runtime.agent_team_runtime import AgentTeamRuntime
from autobyteus.agent_team.events.agent_team_events import ProcessUserMessageEvent

@pytest.mark.asyncio
@patch('autobyteus.agent_team.runtime.agent_team_runtime.AgentTeamWorker')
async def test_submit_event_enqueues_correctly(MockWorker, agent_team_context):
    """Tests that submit_event routes different events to the correct queue."""
    mock_worker_instance = MockWorker.return_value
    # Mock the schedule_coroutine to immediately run the coro
    import concurrent.futures
    def run_coro_immediately(coro_factory):
        # Schedule the coroutine execution on the loop
        asyncio.create_task(coro_factory())
        # Return a done Future to satisfy asyncio.wrap_future
        f = concurrent.futures.Future()
        f.set_result(None)
        return f
    mock_worker_instance.schedule_coroutine.side_effect = run_coro_immediately

    registry = MagicMock()
    runtime = AgentTeamRuntime(agent_team_context, registry)
    
    # Test ProcessUserMessageEvent
    user_message_event = ProcessUserMessageEvent(user_message=MagicMock(), target_agent_name="test")
    await runtime.submit_event(user_message_event)
    
    queue_manager = agent_team_context.state.input_event_queues
    queue_manager.enqueue_user_message.assert_awaited_once_with(user_message_event)
    queue_manager.enqueue_internal_system_event.assert_not_awaited()

    # Test other event
    queue_manager.reset_mock()
    other_event = MagicMock()
    await runtime.submit_event(other_event)
    queue_manager.enqueue_user_message.assert_not_awaited()
    queue_manager.enqueue_internal_system_event.assert_awaited_once_with(other_event)
