import pytest
import logging
import json
from unittest.mock import MagicMock, patch, call

from autobyteus.agent.handlers.tool_execution_approval_event_handler import ToolExecutionApprovalEventHandler
from autobyteus.agent.events.agent_events import ToolExecutionApprovalEvent, ApprovedToolInvocationEvent, LLMPromptReadyEvent, GenericEvent
from autobyteus.agent.tool_invocation import ToolInvocation
from autobyteus.llm.user_message import LLMUserMessage

@pytest.fixture
def tool_approval_handler():
    return ToolExecutionApprovalEventHandler()

@pytest.mark.asyncio
async def test_handle_tool_approved(tool_approval_handler: ToolExecutionApprovalEventHandler, agent_context, mock_tool_invocation, caplog):
    """Test handling when a tool execution is approved."""
    event = ToolExecutionApprovalEvent(tool_invocation_id=mock_tool_invocation.id, is_approved=True, reason="User approved")
    
    # Make retrieve_pending_tool_invocation return our mock_tool_invocation
    agent_context.retrieve_pending_tool_invocation = MagicMock(return_value=mock_tool_invocation)

    with caplog.at_level(logging.INFO):
        await tool_approval_handler.handle(event, agent_context)

    # Check logs
    assert f"Agent '{agent_context.agent_id}' handling ToolExecutionApprovalEvent for tool_invocation_id '{mock_tool_invocation.id}': Approved=True" in caplog.text
    assert f"Tool invocation '{mock_tool_invocation.name}' (ID: {mock_tool_invocation.id}) was APPROVED." in caplog.text
    
    # Check that retrieve_pending_tool_invocation was called
    agent_context.retrieve_pending_tool_invocation.assert_called_once_with(mock_tool_invocation.id)

    # Check that ApprovedToolInvocationEvent was enqueued
    agent_context.queues.enqueue_internal_system_event.assert_called_once()
    enqueued_event = agent_context.queues.enqueue_internal_system_event.call_args[0][0]
    assert isinstance(enqueued_event, ApprovedToolInvocationEvent)
    assert enqueued_event.tool_invocation == mock_tool_invocation

    # Ensure no LLMPromptReadyEvent was enqueued (since it was approved)
    for call_item in agent_context.queues.enqueue_internal_system_event.call_args_list:
        assert not isinstance(call_item[0][0], LLMPromptReadyEvent)
    
    # Ensure history was NOT updated directly by this handler for approval path
    agent_context.add_message_to_history.assert_not_called()


@pytest.mark.asyncio
async def test_handle_tool_denied(tool_approval_handler: ToolExecutionApprovalEventHandler, agent_context, mock_tool_invocation, caplog):
    """Test handling when a tool execution is denied."""
    denial_reason = "User denied due to cost."
    event = ToolExecutionApprovalEvent(tool_invocation_id=mock_tool_invocation.id, is_approved=False, reason=denial_reason)
    
    agent_context.retrieve_pending_tool_invocation = MagicMock(return_value=mock_tool_invocation)

    with caplog.at_level(logging.WARNING): # Denial logs at WARNING
        await tool_approval_handler.handle(event, agent_context)

    assert f"Tool invocation '{mock_tool_invocation.name}' (ID: {mock_tool_invocation.id}) was DENIED. Reason: '{denial_reason}'." in caplog.text
    assert "Informing LLM." in caplog.text

    agent_context.retrieve_pending_tool_invocation.assert_called_once_with(mock_tool_invocation.id)

    # Check history update for denial
    expected_history_content = f"Tool execution denied by user/system. Reason: {denial_reason}"
    agent_context.add_message_to_history.assert_called_once_with({
        "role": "tool",
        "tool_call_id": mock_tool_invocation.id,
        "name": mock_tool_invocation.name,
        "content": expected_history_content,
    })

    # Check that LLMPromptReadyEvent was enqueued to inform LLM
    agent_context.queues.enqueue_internal_system_event.assert_called_once()
    enqueued_event = agent_context.queues.enqueue_internal_system_event.call_args[0][0]
    assert isinstance(enqueued_event, LLMPromptReadyEvent)
    assert isinstance(enqueued_event.llm_user_message, LLMUserMessage)
    
    expected_llm_prompt = (
        f"The request to use the tool '{mock_tool_invocation.name}' "
        f"(with arguments: {json.dumps(mock_tool_invocation.arguments or {})}) was denied. "
        f"Denial reason: '{denial_reason}'. "
        "Please analyze this outcome and the conversation history, then decide on the next course of action."
    )
    assert enqueued_event.llm_user_message.content == expected_llm_prompt

    # Ensure no ApprovedToolInvocationEvent was enqueued
    for call_item in agent_context.queues.enqueue_internal_system_event.call_args_list:
        assert not isinstance(call_item[0][0], ApprovedToolInvocationEvent)


@pytest.mark.asyncio
async def test_handle_tool_denied_no_reason(tool_approval_handler: ToolExecutionApprovalEventHandler, agent_context, mock_tool_invocation, caplog):
    """Test tool denial when no reason is provided."""
    event = ToolExecutionApprovalEvent(tool_invocation_id=mock_tool_invocation.id, is_approved=False, reason=None)
    agent_context.retrieve_pending_tool_invocation = MagicMock(return_value=mock_tool_invocation)

    await tool_approval_handler.handle(event, agent_context)

    expected_denial_reason_str = "No specific reason provided."
    # Check history content
    expected_history_content = f"Tool execution denied by user/system. Reason: {expected_denial_reason_str}"
    agent_context.add_message_to_history.assert_called_once_with({
        "role": "tool",
        "tool_call_id": mock_tool_invocation.id,
        "name": mock_tool_invocation.name,
        "content": expected_history_content,
    })
    # Check LLM prompt content
    enqueued_event = agent_context.queues.enqueue_internal_system_event.call_args[0][0]
    assert f"Denial reason: '{expected_denial_reason_str}'." in enqueued_event.llm_user_message.content


@pytest.mark.asyncio
async def test_handle_pending_invocation_not_found(tool_approval_handler: ToolExecutionApprovalEventHandler, agent_context, caplog):
    """Test when retrieve_pending_tool_invocation returns None."""
    unknown_invocation_id = "unknown-id-000"
    event = ToolExecutionApprovalEvent(tool_invocation_id=unknown_invocation_id, is_approved=True)
    
    agent_context.retrieve_pending_tool_invocation = MagicMock(return_value=None) # Simulate not found

    with caplog.at_level(logging.WARNING):
        await tool_approval_handler.handle(event, agent_context)

    assert f"Agent '{agent_context.agent_id}': No pending tool invocation found for ID '{unknown_invocation_id}'." in caplog.text
    
    agent_context.retrieve_pending_tool_invocation.assert_called_once_with(unknown_invocation_id)
    agent_context.queues.enqueue_internal_system_event.assert_not_called()
    agent_context.add_message_to_history.assert_not_called()


@pytest.mark.asyncio
async def test_handle_invalid_event_type(tool_approval_handler: ToolExecutionApprovalEventHandler, agent_context, caplog):
    """Test that the handler skips events that are not ToolExecutionApprovalEvent."""
    invalid_event = GenericEvent(payload={}, type_name="some_other_event")

    with caplog.at_level(logging.WARNING):
        await tool_approval_handler.handle(invalid_event, agent_context) # type: ignore
    
    assert f"ToolExecutionApprovalEventHandler received non-ToolExecutionApprovalEvent: {type(invalid_event)}. Skipping." in caplog.text
    agent_context.retrieve_pending_tool_invocation.assert_not_called()
    agent_context.queues.enqueue_internal_system_event.assert_not_called()
    agent_context.add_message_to_history.assert_not_called()


def test_tool_approval_handler_initialization(caplog):
    with caplog.at_level(logging.INFO):
        handler = ToolExecutionApprovalEventHandler()
    assert "ToolExecutionApprovalEventHandler initialized." in caplog.text

