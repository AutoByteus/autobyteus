import pytest
import logging

from autobyteus.agent.handlers.tool_invocation_request_event_handler import ToolInvocationRequestEventHandler
from autobyteus.agent.events.agent_events import PendingToolInvocationEvent, ExecuteToolInvocationEvent, GenericEvent


@pytest.fixture
def tool_request_handler():
    return ToolInvocationRequestEventHandler()


@pytest.mark.asyncio
async def test_handle_approval_required_logic(
    tool_request_handler: ToolInvocationRequestEventHandler,
    agent_context,
    mock_tool_invocation,
    caplog,
):
    agent_context.config.auto_execute_tools = False
    event = PendingToolInvocationEvent(tool_invocation=mock_tool_invocation)

    agent_context.status_manager.notifier = agent_context.status_manager.notifier

    with caplog.at_level(logging.DEBUG):
        await tool_request_handler.handle(event, agent_context)

    agent_context.state.store_pending_tool_invocation.assert_called_once_with(mock_tool_invocation)

    expected_approval_data = {
        "agent_id": agent_context.agent_id,
        "invocation_id": mock_tool_invocation.id,
        "tool_name": mock_tool_invocation.name,
        "turn_id": mock_tool_invocation.turn_id,
        "arguments": mock_tool_invocation.arguments,
    }
    agent_context.status_manager.notifier.notify_agent_tool_approval_requested.assert_called_once_with(
        expected_approval_data
    )

    agent_context.input_event_queues.enqueue_internal_system_event.assert_not_called()


@pytest.mark.asyncio
async def test_handle_approval_required_notifier_missing(tool_request_handler: ToolInvocationRequestEventHandler, agent_context, mock_tool_invocation, caplog):
    agent_context.config.auto_execute_tools = False
    agent_context.status_manager.notifier = None
    event = PendingToolInvocationEvent(tool_invocation=mock_tool_invocation)

    with caplog.at_level(logging.ERROR):
        await tool_request_handler.handle(event, agent_context)

    assert "Notifier is required for manual approval flow but unavailable" in caplog.text
    agent_context.state.store_pending_tool_invocation.assert_not_called()


@pytest.mark.asyncio
async def test_handle_auto_execute_enqueues_execution_event(tool_request_handler: ToolInvocationRequestEventHandler, agent_context, mock_tool_invocation):
    agent_context.config.auto_execute_tools = True
    event = PendingToolInvocationEvent(tool_invocation=mock_tool_invocation)

    await tool_request_handler.handle(event, agent_context)

    agent_context.state.store_pending_tool_invocation.assert_not_called()
    agent_context.input_event_queues.enqueue_internal_system_event.assert_called_once()

    enqueued_event = agent_context.input_event_queues.enqueue_internal_system_event.call_args[0][0]
    assert isinstance(enqueued_event, ExecuteToolInvocationEvent)
    assert enqueued_event.tool_invocation == mock_tool_invocation


@pytest.mark.asyncio
async def test_handle_invalid_event_type(tool_request_handler: ToolInvocationRequestEventHandler, agent_context, caplog):
    invalid_event = GenericEvent(payload={}, type_name="other_event")

    with caplog.at_level(logging.WARNING):
        await tool_request_handler.handle(invalid_event, agent_context)

    assert "ToolInvocationRequestEventHandler received non-PendingToolInvocationEvent" in caplog.text
    agent_context.state.store_pending_tool_invocation.assert_not_called()


def test_tool_request_handler_initialization(caplog):
    with caplog.at_level(logging.INFO):
        ToolInvocationRequestEventHandler()
    assert "ToolInvocationRequestEventHandler initialized." in caplog.text
