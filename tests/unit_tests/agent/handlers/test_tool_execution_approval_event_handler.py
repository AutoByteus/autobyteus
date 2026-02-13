import pytest
import logging

from autobyteus.agent.handlers.tool_execution_approval_event_handler import ToolExecutionApprovalEventHandler
from autobyteus.agent.events.agent_events import (
    ToolExecutionApprovalEvent,
    ExecuteToolInvocationEvent,
    ToolResultEvent,
    GenericEvent,
)


@pytest.fixture
def tool_approval_handler():
    return ToolExecutionApprovalEventHandler()


@pytest.mark.asyncio
async def test_handle_tool_approved(
    tool_approval_handler: ToolExecutionApprovalEventHandler,
    agent_context,
    mock_tool_invocation,
    caplog,
):
    event = ToolExecutionApprovalEvent(
        tool_invocation_id=mock_tool_invocation.id,
        is_approved=True,
        reason="User approved",
    )

    agent_context.state.retrieve_pending_tool_invocation.return_value = mock_tool_invocation

    with caplog.at_level(logging.INFO):
        await tool_approval_handler.handle(event, agent_context)

    agent_context.state.retrieve_pending_tool_invocation.assert_called_once_with(mock_tool_invocation.id)
    agent_context.status_manager.notifier.notify_agent_tool_approved.assert_called_once()

    agent_context.input_event_queues.enqueue_internal_system_event.assert_called_once()
    enqueued_event = agent_context.input_event_queues.enqueue_internal_system_event.call_args[0][0]
    assert isinstance(enqueued_event, ExecuteToolInvocationEvent)
    assert enqueued_event.tool_invocation == mock_tool_invocation


@pytest.mark.asyncio
async def test_handle_tool_denied(tool_approval_handler: ToolExecutionApprovalEventHandler, agent_context, mock_tool_invocation):
    denial_reason = "User denied due to cost."
    event = ToolExecutionApprovalEvent(
        tool_invocation_id=mock_tool_invocation.id,
        is_approved=False,
        reason=denial_reason,
    )

    agent_context.state.retrieve_pending_tool_invocation.return_value = mock_tool_invocation

    await tool_approval_handler.handle(event, agent_context)

    agent_context.state.retrieve_pending_tool_invocation.assert_called_once_with(mock_tool_invocation.id)
    agent_context.status_manager.notifier.notify_agent_tool_denied.assert_called_once()

    agent_context.input_event_queues.enqueue_tool_result.assert_called_once()
    enqueued_event = agent_context.input_event_queues.enqueue_tool_result.call_args[0][0]
    assert isinstance(enqueued_event, ToolResultEvent)
    assert enqueued_event.tool_name == mock_tool_invocation.name
    assert enqueued_event.error == denial_reason
    assert enqueued_event.is_denied is True


@pytest.mark.asyncio
async def test_handle_tool_denied_no_reason(tool_approval_handler: ToolExecutionApprovalEventHandler, agent_context, mock_tool_invocation):
    event = ToolExecutionApprovalEvent(tool_invocation_id=mock_tool_invocation.id, is_approved=False, reason=None)
    agent_context.state.retrieve_pending_tool_invocation.return_value = mock_tool_invocation

    await tool_approval_handler.handle(event, agent_context)

    enqueued_event = agent_context.input_event_queues.enqueue_tool_result.call_args[0][0]
    assert enqueued_event.error == "Tool execution was denied by user/system."


@pytest.mark.asyncio
async def test_handle_pending_invocation_not_found(tool_approval_handler: ToolExecutionApprovalEventHandler, agent_context, caplog):
    unknown_invocation_id = "unknown-id-000"
    event = ToolExecutionApprovalEvent(tool_invocation_id=unknown_invocation_id, is_approved=True)

    agent_context.state.retrieve_pending_tool_invocation.return_value = None

    with caplog.at_level(logging.WARNING):
        await tool_approval_handler.handle(event, agent_context)

    assert f"No pending tool invocation found for ID '{unknown_invocation_id}'" in caplog.text
    agent_context.state.retrieve_pending_tool_invocation.assert_called_once_with(unknown_invocation_id)
    agent_context.input_event_queues.enqueue_internal_system_event.assert_not_called()
    agent_context.input_event_queues.enqueue_tool_result.assert_not_called()


@pytest.mark.asyncio
async def test_handle_invalid_event_type(tool_approval_handler: ToolExecutionApprovalEventHandler, agent_context, caplog):
    invalid_event = GenericEvent(payload={}, type_name="some_other_event")

    with caplog.at_level(logging.WARNING):
        await tool_approval_handler.handle(invalid_event, agent_context)

    assert "ToolExecutionApprovalEventHandler received non-ToolExecutionApprovalEvent" in caplog.text
    agent_context.state.retrieve_pending_tool_invocation.assert_not_called()


def test_tool_approval_handler_initialization(caplog):
    with caplog.at_level(logging.INFO):
        ToolExecutionApprovalEventHandler()
    assert "ToolExecutionApprovalEventHandler initialized." in caplog.text
