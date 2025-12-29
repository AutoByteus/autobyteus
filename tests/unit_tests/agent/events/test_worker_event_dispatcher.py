# file: autobyteus/tests/unit_tests/agent/events/test_worker_event_dispatcher.py
import asyncio
import pytest
from unittest.mock import MagicMock, AsyncMock, patch, call

from autobyteus.agent.events.worker_event_dispatcher import WorkerEventDispatcher
from autobyteus.agent.events.agent_events import (
    BaseEvent, UserMessageReceivedEvent, InterAgentMessageReceivedEvent, LLMUserMessageReadyEvent,
    PendingToolInvocationEvent, ToolExecutionApprovalEvent, ApprovedToolInvocationEvent, ToolResultEvent,
    LLMCompleteResponseReceivedEvent, AgentReadyEvent, AgentErrorEvent, AgentIdleEvent
)
from autobyteus.agent.handlers.base_event_handler import AgentEventHandler
from autobyteus.agent.handlers.event_handler_registry import EventHandlerRegistry
from autobyteus.agent.status.status_enum import AgentStatus
from autobyteus.agent.context.agent_context import AgentContext
from autobyteus.agent.tool_invocation import ToolInvocation
from autobyteus.llm.utils.response_types import CompleteResponse


@pytest.fixture
def mock_event_handler_registry():
    return MagicMock(spec=EventHandlerRegistry)

# Removed local mock_status_manager and mock_agent_context fixtures.
# The tests will now use the more robust shared fixtures from agent/conftest.py.

@pytest.fixture
def mock_event_handler():
    handler = MagicMock(spec=AgentEventHandler)
    handler.handle = AsyncMock()
    # Set a __name__ for the mock handler's class type, as WorkerEventDispatcher uses it in logs/errors
    type(handler).__name__ = "MockEventHandlerClass" 
    return handler

def _set_status(agent_context: AgentContext, status: AgentStatus) -> None:
    agent_context.current_status = status
    agent_context.state.status_deriver._current_status = status

def _assert_status_update(mock_status_manager, old_status: AgentStatus, new_status: AgentStatus, additional_data):
    call_args, call_kwargs = mock_status_manager.emit_status_update.call_args
    assert call_args == (old_status, new_status)
    assert call_kwargs.get("additional_data") == additional_data

@pytest.fixture
def worker_event_dispatcher(mock_event_handler_registry):
    return WorkerEventDispatcher(event_handler_registry=mock_event_handler_registry)

@pytest.mark.asyncio
async def test_dispatch_no_handler(worker_event_dispatcher, agent_context, mock_event_handler_registry):
    event = BaseEvent()
    mock_event_handler_registry.get_handler.return_value = None

    with patch('autobyteus.agent.events.worker_event_dispatcher.logger') as mock_logger:
        await worker_event_dispatcher.dispatch(event, agent_context)
        mock_logger.warning.assert_called_once()
        assert "No handler for 'BaseEvent'" in mock_logger.warning.call_args[0][0]
        agent_context.status_manager.emit_status_update.assert_not_awaited()

@pytest.mark.asyncio
async def test_dispatch_successful_handling(worker_event_dispatcher, agent_context, mock_event_handler_registry, mock_event_handler):
    event = UserMessageReceivedEvent(agent_input_user_message=MagicMock())
    mock_event_handler_registry.get_handler.return_value = mock_event_handler

    await worker_event_dispatcher.dispatch(event, agent_context)
    mock_event_handler.handle.assert_awaited_once_with(event, agent_context)
    agent_context.status_manager.emit_status_update.assert_awaited_once()
    _assert_status_update(
        agent_context.status_manager,
        AgentStatus.IDLE,
        AgentStatus.PROCESSING_USER_INPUT,
        {"trigger": "UserMessageReceivedEvent"},
    )

@pytest.mark.asyncio
async def test_dispatch_handler_raises_exception(worker_event_dispatcher, agent_context, mock_event_handler_registry, mock_event_handler):
    event = UserMessageReceivedEvent(agent_input_user_message=MagicMock())
    mock_event_handler_registry.get_handler.return_value = mock_event_handler
    test_exception = ValueError("Handler failed")
    mock_event_handler.handle.side_effect = test_exception

    with patch('autobyteus.agent.events.worker_event_dispatcher.logger') as mock_logger:
        await worker_event_dispatcher.dispatch(event, agent_context)

        mock_logger.error.assert_called_once()
        expected_log_error_substring = f"error handling 'UserMessageReceivedEvent' with {type(mock_event_handler).__name__}: Handler failed"
        assert expected_log_error_substring in mock_logger.error.call_args[0][0]
        agent_context.input_event_queues.enqueue_internal_system_event.assert_awaited_once()
        enqueued_event = agent_context.input_event_queues.enqueue_internal_system_event.call_args[0][0]
        assert isinstance(enqueued_event, AgentErrorEvent)
        assert expected_log_error_substring in enqueued_event.error_message
        assert "Traceback" in enqueued_event.exception_details


# --- Pre-Handler Status Transition Tests ---
@pytest.mark.asyncio
async def test_dispatch_user_message_from_idle_triggers_processing_status(worker_event_dispatcher, agent_context, mock_event_handler_registry, mock_event_handler):
    _set_status(agent_context, AgentStatus.IDLE)
    event = UserMessageReceivedEvent(agent_input_user_message=MagicMock())
    mock_event_handler_registry.get_handler.return_value = mock_event_handler

    await worker_event_dispatcher.dispatch(event, agent_context)
    agent_context.status_manager.emit_status_update.assert_awaited_once()
    _assert_status_update(
        agent_context.status_manager,
        AgentStatus.IDLE,
        AgentStatus.PROCESSING_USER_INPUT,
        {"trigger": "UserMessageReceivedEvent"},
    )

@pytest.mark.asyncio
async def test_dispatch_inter_agent_message_from_idle_triggers_processing_status(worker_event_dispatcher, agent_context, mock_event_handler_registry, mock_event_handler):
    _set_status(agent_context, AgentStatus.IDLE)
    event = InterAgentMessageReceivedEvent(inter_agent_message=MagicMock())
    mock_event_handler_registry.get_handler.return_value = mock_event_handler

    await worker_event_dispatcher.dispatch(event, agent_context)
    agent_context.status_manager.emit_status_update.assert_awaited_once()
    _assert_status_update(
        agent_context.status_manager,
        AgentStatus.IDLE,
        AgentStatus.PROCESSING_USER_INPUT,
        {"trigger": "InterAgentMessageReceivedEvent"},
    )

@pytest.mark.asyncio
async def test_dispatch_llm_user_message_ready_triggers_awaiting_llm_status(worker_event_dispatcher, agent_context, mock_event_handler_registry, mock_event_handler):
    _set_status(agent_context, AgentStatus.PROCESSING_USER_INPUT)
    event = LLMUserMessageReadyEvent(llm_user_message=MagicMock())
    mock_event_handler_registry.get_handler.return_value = mock_event_handler

    await worker_event_dispatcher.dispatch(event, agent_context)
    agent_context.status_manager.emit_status_update.assert_awaited_once()
    _assert_status_update(
        agent_context.status_manager,
        AgentStatus.PROCESSING_USER_INPUT,
        AgentStatus.AWAITING_LLM_RESPONSE,
        None,
    )

@pytest.mark.asyncio
async def test_dispatch_pending_tool_invocation_auto_execute_true(worker_event_dispatcher, agent_context, mock_event_handler_registry, mock_event_handler):
    agent_context.config.auto_execute_tools = True
    tool_invocation = ToolInvocation(name="test_tool", arguments={}, id="tid1")
    event = PendingToolInvocationEvent(tool_invocation=tool_invocation)
    mock_event_handler_registry.get_handler.return_value = mock_event_handler

    await worker_event_dispatcher.dispatch(event, agent_context)
    agent_context.status_manager.emit_status_update.assert_awaited_once()
    _assert_status_update(
        agent_context.status_manager,
        AgentStatus.IDLE,
        AgentStatus.EXECUTING_TOOL,
        {"tool_name": "test_tool"},
    )

@pytest.mark.asyncio
async def test_dispatch_pending_tool_invocation_auto_execute_false(worker_event_dispatcher, agent_context, mock_event_handler_registry, mock_event_handler):
    agent_context.config.auto_execute_tools = False
    tool_invocation = ToolInvocation(name="test_tool", arguments={}, id="tid1")
    event = PendingToolInvocationEvent(tool_invocation=tool_invocation)
    mock_event_handler_registry.get_handler.return_value = mock_event_handler

    await worker_event_dispatcher.dispatch(event, agent_context)
    agent_context.status_manager.emit_status_update.assert_awaited_once()
    _assert_status_update(
        agent_context.status_manager,
        AgentStatus.IDLE,
        AgentStatus.AWAITING_TOOL_APPROVAL,
        None,
    )

@pytest.mark.asyncio
async def test_dispatch_tool_execution_approval_approved(worker_event_dispatcher, agent_context, mock_event_handler_registry, mock_event_handler):
    tool_invocation_id = "tid1"
    agent_context.state.pending_tool_approvals = {tool_invocation_id: ToolInvocation(name="approved_tool", id=tool_invocation_id)}
    _set_status(agent_context, AgentStatus.AWAITING_TOOL_APPROVAL)
    
    event = ToolExecutionApprovalEvent(tool_invocation_id=tool_invocation_id, is_approved=True)
    mock_event_handler_registry.get_handler.return_value = mock_event_handler

    await worker_event_dispatcher.dispatch(event, agent_context)
    agent_context.status_manager.emit_status_update.assert_awaited_once()
    _assert_status_update(
        agent_context.status_manager,
        AgentStatus.AWAITING_TOOL_APPROVAL,
        AgentStatus.EXECUTING_TOOL,
        {"tool_name": "approved_tool"},
    )

@pytest.mark.asyncio
async def test_dispatch_tool_execution_approval_denied(worker_event_dispatcher, agent_context, mock_event_handler_registry, mock_event_handler):
    tool_invocation_id = "tid2"
    agent_context.state.pending_tool_approvals = {tool_invocation_id: ToolInvocation(name="denied_tool", id=tool_invocation_id)}
    _set_status(agent_context, AgentStatus.AWAITING_TOOL_APPROVAL)
    
    event = ToolExecutionApprovalEvent(tool_invocation_id=tool_invocation_id, is_approved=False)
    mock_event_handler_registry.get_handler.return_value = mock_event_handler

    await worker_event_dispatcher.dispatch(event, agent_context)
    agent_context.status_manager.emit_status_update.assert_awaited_once()
    _assert_status_update(
        agent_context.status_manager,
        AgentStatus.AWAITING_TOOL_APPROVAL,
        AgentStatus.TOOL_DENIED,
        {"tool_name": "denied_tool", "denial_for_tool": "denied_tool"},
    )

@pytest.mark.asyncio
async def test_dispatch_tool_result_triggers_processing_result_status(worker_event_dispatcher, agent_context, mock_event_handler_registry, mock_event_handler):
    _set_status(agent_context, AgentStatus.EXECUTING_TOOL)
    event = ToolResultEvent(tool_name="test_tool_result", result="some_result")
    mock_event_handler_registry.get_handler.return_value = mock_event_handler

    await worker_event_dispatcher.dispatch(event, agent_context)
    agent_context.status_manager.emit_status_update.assert_awaited_once()
    _assert_status_update(
        agent_context.status_manager,
        AgentStatus.EXECUTING_TOOL,
        AgentStatus.PROCESSING_TOOL_RESULT,
        {"tool_name": "test_tool_result"},
    )

@pytest.mark.asyncio
async def test_dispatch_llm_complete_response_triggers_analyzing_status(worker_event_dispatcher, agent_context, mock_event_handler_registry, mock_event_handler):
    _set_status(agent_context, AgentStatus.AWAITING_LLM_RESPONSE)
    response_obj = CompleteResponse(content="Response text")
    event = LLMCompleteResponseReceivedEvent(complete_response=response_obj)
    mock_event_handler_registry.get_handler.return_value = mock_event_handler

    await worker_event_dispatcher.dispatch(event, agent_context)
    agent_context.status_manager.emit_status_update.assert_awaited_once()
    _assert_status_update(
        agent_context.status_manager,
        AgentStatus.AWAITING_LLM_RESPONSE,
        AgentStatus.ANALYZING_LLM_RESPONSE,
        None,
    )

# --- Post-Handler Status Transition Tests ---
@pytest.mark.asyncio
async def test_dispatch_agent_ready_event_triggers_initialization_complete(worker_event_dispatcher, agent_context, mock_event_handler_registry, mock_event_handler):
    event = AgentReadyEvent()
    mock_event_handler_registry.get_handler.return_value = mock_event_handler
    _set_status(agent_context, AgentStatus.BOOTSTRAPPING)

    await worker_event_dispatcher.dispatch(event, agent_context)
    
    mock_event_handler.handle.assert_awaited_once_with(event, agent_context)
    agent_context.status_manager.emit_status_update.assert_awaited_once()
    _assert_status_update(
        agent_context.status_manager,
        AgentStatus.BOOTSTRAPPING,
        AgentStatus.IDLE,
        None,
    )


@pytest.mark.asyncio
async def test_dispatch_llm_complete_response_to_idle(worker_event_dispatcher, agent_context, mock_event_handler_registry, mock_event_handler):
    _set_status(agent_context, AgentStatus.AWAITING_LLM_RESPONSE)
    agent_context.state.pending_tool_approvals.clear()
    agent_context.input_event_queues.tool_invocation_request_queue.empty.return_value = True
    
    response_obj = CompleteResponse(content="Response text")
    event = LLMCompleteResponseReceivedEvent(complete_response=response_obj)
    mock_event_handler_registry.get_handler.return_value = mock_event_handler

    await worker_event_dispatcher.dispatch(event, agent_context)
    
    mock_event_handler.handle.assert_awaited_once_with(event, agent_context)
    agent_context.status_manager.emit_status_update.assert_awaited_once()
    _assert_status_update(
        agent_context.status_manager,
        AgentStatus.AWAITING_LLM_RESPONSE,
        AgentStatus.ANALYZING_LLM_RESPONSE,
        None,
    )
    agent_context.input_event_queues.enqueue_internal_system_event.assert_awaited_once()
    enqueued_event = agent_context.input_event_queues.enqueue_internal_system_event.call_args[0][0]
    assert isinstance(enqueued_event, AgentIdleEvent)


@pytest.mark.asyncio
async def test_dispatch_llm_complete_not_to_idle_if_pending_approvals(worker_event_dispatcher, agent_context, mock_event_handler_registry, mock_event_handler):
    _set_status(agent_context, AgentStatus.AWAITING_LLM_RESPONSE)
    agent_context.state.pending_tool_approvals = {"tid1": MagicMock()}
    agent_context.input_event_queues.tool_invocation_request_queue.empty.return_value = True
    
    response_obj = CompleteResponse(content="Response text")
    event = LLMCompleteResponseReceivedEvent(complete_response=response_obj)
    mock_event_handler_registry.get_handler.return_value = mock_event_handler

    await worker_event_dispatcher.dispatch(event, agent_context)
    agent_context.input_event_queues.enqueue_internal_system_event.assert_not_awaited()

@pytest.mark.asyncio
async def test_dispatch_llm_complete_not_to_idle_if_tool_requests_pending(worker_event_dispatcher, agent_context, mock_event_handler_registry, mock_event_handler):
    _set_status(agent_context, AgentStatus.AWAITING_LLM_RESPONSE)
    agent_context.state.pending_tool_approvals.clear()
    agent_context.input_event_queues.tool_invocation_request_queue.empty.return_value = False
    
    response_obj = CompleteResponse(content="Response text")
    event = LLMCompleteResponseReceivedEvent(complete_response=response_obj)
    mock_event_handler_registry.get_handler.return_value = mock_event_handler

    await worker_event_dispatcher.dispatch(event, agent_context)
    agent_context.input_event_queues.enqueue_internal_system_event.assert_not_awaited()

# --- No Transition Scenarios ---
@pytest.mark.asyncio
async def test_dispatch_user_message_not_from_idle_no_processing_status_trigger(worker_event_dispatcher, agent_context, mock_event_handler_registry, mock_event_handler):
    _set_status(agent_context, AgentStatus.PROCESSING_USER_INPUT)
    event = UserMessageReceivedEvent(agent_input_user_message=MagicMock())
    mock_event_handler_registry.get_handler.return_value = mock_event_handler

    await worker_event_dispatcher.dispatch(event, agent_context)
    agent_context.status_manager.emit_status_update.assert_not_awaited()

@pytest.mark.asyncio
async def test_dispatch_llm_user_message_ready_if_already_awaiting_llm_or_error(worker_event_dispatcher, agent_context, mock_event_handler_registry, mock_event_handler):
    test_statuss = [AgentStatus.AWAITING_LLM_RESPONSE, AgentStatus.ERROR]
    for status in test_statuss:
        _set_status(agent_context, status)
        agent_context.status_manager.reset_mock()
        
        event = LLMUserMessageReadyEvent(llm_user_message=MagicMock())
        mock_event_handler_registry.get_handler.return_value = mock_event_handler

        await worker_event_dispatcher.dispatch(event, agent_context)
        agent_context.status_manager.emit_status_update.assert_not_awaited()

@pytest.mark.asyncio
async def test_tool_execution_approval_tool_name_resolution_failure(worker_event_dispatcher, agent_context, mock_event_handler_registry, mock_event_handler):
    tool_invocation_id = "tid_unknown"
    agent_context.state.pending_tool_approvals = {}
    _set_status(agent_context, AgentStatus.AWAITING_TOOL_APPROVAL)
    
    event = ToolExecutionApprovalEvent(tool_invocation_id=tool_invocation_id, is_approved=True)
    mock_event_handler_registry.get_handler.return_value = mock_event_handler

    await worker_event_dispatcher.dispatch(event, agent_context)
    agent_context.status_manager.emit_status_update.assert_awaited_once()
    _assert_status_update(
        agent_context.status_manager,
        AgentStatus.AWAITING_TOOL_APPROVAL,
        AgentStatus.EXECUTING_TOOL,
        {"tool_name": "unknown_tool"},
    )

@pytest.mark.asyncio
async def test_dispatch_agent_ready_event_call_order(worker_event_dispatcher, agent_context, mock_event_handler_registry, mock_event_handler):
    """Test the call order for AgentReadyEvent more directly."""
    event = AgentReadyEvent()
    mock_event_handler_registry.get_handler.return_value = mock_event_handler
    _set_status(agent_context, AgentStatus.BOOTSTRAPPING)

    await worker_event_dispatcher.dispatch(event, agent_context)

    mock_event_handler.handle.assert_awaited_once_with(event, agent_context)
    agent_context.status_manager.emit_status_update.assert_awaited_once()

@pytest.mark.asyncio
async def test_dispatch_agent_ready_event_call_order_strict(worker_event_dispatcher, agent_context, mock_event_handler_registry, mock_event_handler):
    """A stricter version of the call order test."""
    event = AgentReadyEvent()
    mock_event_handler_registry.get_handler.return_value = mock_event_handler
    _set_status(agent_context, AgentStatus.BOOTSTRAPPING)

    manager = MagicMock()
    manager.attach_mock(mock_event_handler, 'handler_mock')
    manager.attach_mock(agent_context.status_manager, 'status_manager_mock')

    await worker_event_dispatcher.dispatch(event, agent_context)

    expected_calls = [
        call.status_manager_mock.emit_status_update(AgentStatus.BOOTSTRAPPING, AgentStatus.IDLE, additional_data=None),
        call.handler_mock.handle(event, agent_context),
    ]
    manager.assert_has_calls(expected_calls, any_order=False)
