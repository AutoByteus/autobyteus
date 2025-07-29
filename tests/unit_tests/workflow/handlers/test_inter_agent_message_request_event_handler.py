# file: autobyteus/tests/unit_tests/workflow/handlers/test_inter_agent_message_request_event_handler.py
import pytest
from unittest.mock import MagicMock, AsyncMock, patch

from autobyteus.workflow.handlers.inter_agent_message_request_event_handler import InterAgentMessageRequestEventHandler
from autobyteus.workflow.events.workflow_events import InterAgentMessageRequestEvent
from autobyteus.workflow.context import WorkflowContext
from autobyteus.agent.agent import Agent
from autobyteus.agent.message.inter_agent_message import InterAgentMessage
from autobyteus.agent.streaming.stream_events import StreamEventType, StreamEvent
from autobyteus.agent.streaming.stream_event_payloads import AssistantCompleteResponseData

@pytest.fixture
def handler():
    return InterAgentMessageRequestEventHandler()

@pytest.fixture
def mock_sender_agent(workflow_context):
    agent = workflow_context.coordinator_agent
    agent.agent_id = "sender_agent_id_123"
    return agent

@pytest.fixture
def mock_recipient_agent():
    agent = MagicMock(spec=Agent)
    agent.agent_id = "recipient_agent_id_456"
    agent.is_running = False
    agent.start = MagicMock()
    agent.post_inter_agent_message = AsyncMock()
    # Mock the context hierarchy
    agent.context.config.role = "RecipientRole"
    return agent

@pytest.fixture
def event(mock_sender_agent):
    return InterAgentMessageRequestEvent(
        sender_agent_id=mock_sender_agent.agent_id,
        recipient_name="Recipient",
        content="Do the thing",
        message_type="TASK"
    )

@pytest.mark.asyncio
@patch('autobyteus.workflow.handlers.inter_agent_message_request_event_handler.AgentEventStream')
@patch('autobyteus.workflow.handlers.inter_agent_message_request_event_handler.wait_for_agent_to_be_idle', new_callable=AsyncMock)
async def test_handle_happy_path_agent_not_running(
    mock_wait_idle, mock_stream_cls, handler, event, workflow_context, mock_sender_agent, mock_recipient_agent
):
    """
    Tests the full success path where the recipient agent is not running and needs to be started.
    """
    # --- Arrange ---
    workflow_context.team_manager.get_agent_by_friendly_name.return_value = mock_recipient_agent
    
    # Mock the event stream to yield one final result and then end
    async def mock_stream_iterator():
        yield StreamEvent(
            event_type=StreamEventType.ASSISTANT_COMPLETE_RESPONSE,
            data=AssistantCompleteResponseData(content="Task Done")
        )
    mock_stream_instance = MagicMock()
    mock_stream_instance.all_events.return_value = mock_stream_iterator()
    mock_stream_instance.close = AsyncMock()
    mock_stream_cls.return_value = mock_stream_instance

    # --- Act ---
    await handler.handle(event, workflow_context)

    # --- Assert ---
    # Agent startup
    mock_recipient_agent.start.assert_called_once()
    mock_wait_idle.assert_awaited_once_with(mock_recipient_agent, timeout=60.0)
    
    # Message posting
    mock_recipient_agent.post_inter_agent_message.assert_awaited_once()
    
    # Result sent back to sender
    mock_sender_agent.post_inter_agent_message.assert_awaited_once()
    result_message = mock_sender_agent.post_inter_agent_message.call_args[0][0]
    assert isinstance(result_message, InterAgentMessage)
    assert "Task completed by Recipient. Result: Task Done" in result_message.content
    
    # Notifier calls
    notifier = workflow_context.phase_manager.notifier
    assert notifier.notify_agent_activity.call_count >= 3 # Starting, Idle, activity, Completed
    
    # Cleanup
    mock_stream_instance.close.assert_awaited_once()

@pytest.mark.asyncio
@patch('autobyteus.workflow.handlers.inter_agent_message_request_event_handler.wait_for_agent_to_be_idle', new_callable=AsyncMock)
async def test_handle_agent_already_running(mock_wait_idle, handler, event, workflow_context, mock_recipient_agent):
    """Tests that agent.start() is NOT called if the agent is already running."""
    mock_recipient_agent.is_running = True
    workflow_context.team_manager.get_agent_by_friendly_name.return_value = mock_recipient_agent

    # We can stop the test after the check, as we only care about the startup logic
    mock_recipient_agent.post_inter_agent_message.side_effect = StopAsyncIteration

    with pytest.raises(StopAsyncIteration):
        await handler.handle(event, workflow_context)

    mock_recipient_agent.start.assert_not_called()
    mock_wait_idle.assert_not_awaited()

@pytest.mark.asyncio
async def test_handle_recipient_not_found(handler, event, workflow_context):
    """Tests failure when the recipient agent cannot be found."""
    workflow_context.team_manager.get_agent_by_friendly_name.return_value = None
    
    await handler.handle(event, workflow_context)
    
    notifier = workflow_context.phase_manager.notifier
    notifier.notify_agent_activity.assert_called_once_with(
        "Recipient", "Error", "Recipient agent 'Recipient' not found."
    )

@pytest.mark.asyncio
@patch('autobyteus.workflow.handlers.inter_agent_message_request_event_handler.wait_for_agent_to_be_idle', new_callable=AsyncMock)
async def test_handle_agent_startup_fails(mock_wait_idle, handler, event, workflow_context, mock_recipient_agent):
    """Tests failure when the agent startup process fails."""
    mock_wait_idle.side_effect = TimeoutError("Agent timed out")
    workflow_context.team_manager.get_agent_by_friendly_name.return_value = mock_recipient_agent

    await handler.handle(event, workflow_context)

    notifier = workflow_context.phase_manager.notifier
    notifier.notify_agent_activity.assert_any_call("Recipient", "Startup Failed", "Agent timed out")

@pytest.mark.asyncio
@patch('autobyteus.workflow.handlers.inter_agent_message_request_event_handler.AgentEventStream')
@patch('autobyteus.workflow.handlers.inter_agent_message_request_event_handler.wait_for_agent_to_be_idle', new_callable=AsyncMock)
async def test_handle_sub_task_fails(mock_wait_idle, mock_stream_cls, handler, event, workflow_context, mock_recipient_agent):
    """Tests failure during sub-task execution (stream raises exception)."""
    mock_recipient_agent.is_running = True
    workflow_context.team_manager.get_agent_by_friendly_name.return_value = mock_recipient_agent
    
    async def mock_stream_iterator_fail():
        raise RuntimeError("LLM call failed")
        yield # Make it an async generator
    
    mock_stream_instance = MagicMock()
    mock_stream_instance.all_events.return_value = mock_stream_iterator_fail()
    mock_stream_instance.close = AsyncMock()
    mock_stream_cls.return_value = mock_stream_instance
    
    await handler.handle(event, workflow_context)

    notifier = workflow_context.phase_manager.notifier
    notifier.notify_agent_activity.assert_any_call("Recipient", "Execution Error", "LLM call failed")
    mock_stream_instance.close.assert_awaited_once()
