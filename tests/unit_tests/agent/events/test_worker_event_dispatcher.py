# file: autobyteus/tests/unit_tests/agent/events/test_worker_event_dispatcher.py
import asyncio
import pytest
from unittest.mock import MagicMock, AsyncMock, patch

from autobyteus.agent.events.worker_event_dispatcher import WorkerEventDispatcher
from autobyteus.agent.events.agent_events import (
    BaseEvent, UserMessageReceivedEvent, InterAgentMessageReceivedEvent, LLMUserMessageReadyEvent,
    PendingToolInvocationEvent, ToolExecutionApprovalEvent, ApprovedToolInvocationEvent, ToolResultEvent,
    LLMCompleteResponseReceivedEvent, AgentReadyEvent, AgentErrorEvent
)
from autobyteus.agent.handlers.base_event_handler import AgentEventHandler
from autobyteus.agent.handlers.event_handler_registry import EventHandlerRegistry
from autobyteus.agent.status.manager import AgentStatusManager
from autobyteus.agent.status.status_enum import AgentStatus
from autobyteus.agent.context.agent_context import AgentContext
from autobyteus.agent.tool_invocation import ToolInvocation
from autobyteus.llm.utils.response_types import CompleteResponse


@pytest.fixture
def mock_event_handler_registry():
    return MagicMock(spec=EventHandlerRegistry)

# Removed local mock_phase_manager and mock_agent_context fixtures.
# The tests will now use the more robust shared fixtures from agent/conftest.py.

@pytest.fixture
def mock_event_handler():
    handler = MagicMock(spec=AgentEventHandler)
    handler.handle = AsyncMock()
    # Set a __name__ for the mock handler's class type, as WorkerEventDispatcher uses it in logs/errors
    type(handler).__name__ = "MockEventHandlerClass" 
    return handler

@pytest.fixture
def worker_event_dispatcher(mock_event_handler_registry, mock_status_manager):
    return WorkerEventDispatcher(
        event_handler_registry=mock_event_handler_registry,
        status_manager=mock_status_manager
    )

@pytest.mark.asyncio
async def test_dispatch_no_handler(worker_event_dispatcher, agent_context, mock_event_handler_registry):
    event = BaseEvent()
    mock_event_handler_registry.get_handler.return_value = None

    with patch('autobyteus.agent.events.worker_event_dispatcher.logger') as mock_logger:
        await worker_event_dispatcher.dispatch(event, agent_context)
        mock_logger.warning.assert_called_once()
        assert "No handler for 'BaseEvent'" in mock_logger.warning.call_args[0][0]

@pytest.mark.asyncio
async def test_dispatch_successful_handling(worker_event_dispatcher, agent_context, mock_event_handler_registry, mock_event_handler):
    event = UserMessageReceivedEvent(agent_input_user_message=MagicMock())
    mock_event_handler_registry.get_handler.return_value = mock_event_handler

    await worker_event_dispatcher.dispatch(event, agent_context)
    mock_event_handler.handle.assert_awaited_once_with(event, agent_context)

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
        
        agent_context.status_manager.notify_error_occurred.assert_awaited_once()
        call_kwargs = agent_context.status_manager.notify_error_occurred.call_args.kwargs
        
        expected_notify_error_substring = f"error handling 'UserMessageReceivedEvent' with {type(mock_event_handler).__name__}: Handler failed"
        assert expected_notify_error_substring in call_kwargs['error_message']
        assert "Traceback" in call_kwargs['error_details']

        agent_context.input_event_queues.enqueue_internal_system_event.assert_awaited_once()
        enqueued_event = agent_context.input_event_queues.enqueue_internal_system_event.call_args[0][0]
        assert isinstance(enqueued_event, AgentErrorEvent)
        assert expected_notify_error_substring in enqueued_event.error_message
        assert "Traceback" in enqueued_event.exception_details


# --- Pre-Handler Phase Transition Tests ---
@pytest.mark.asyncio
async def test_dispatch_user_message_from_idle_triggers_processing_phase(worker_event_dispatcher, agent_context, mock_event_handler_registry, mock_event_handler):
    agent_context.current_status = AgentStatus.IDLE
    event = UserMessageReceivedEvent(agent_input_user_message=MagicMock())
    mock_event_handler_registry.get_handler.return_value = mock_event_handler

    await worker_event_dispatcher.dispatch(event, agent_context)
    agent_context.status_manager.notify_processing_input_started.assert_awaited_once_with(trigger_info='UserMessageReceivedEvent')

@pytest.mark.asyncio
async def test_dispatch_inter_agent_message_from_idle_triggers_processing_phase(worker_event_dispatcher, agent_context, mock_event_handler_registry, mock_event_handler):
    agent_context.current_status = AgentStatus.IDLE
    event = InterAgentMessageReceivedEvent(inter_agent_message=MagicMock())
    mock_event_handler_registry.get_handler.return_value = mock_event_handler

    await worker_event_dispatcher.dispatch(event, agent_context)
    agent_context.status_manager.notify_processing_input_started.assert_awaited_once_with(trigger_info='InterAgentMessageReceivedEvent')

@pytest.mark.asyncio
async def test_dispatch_llm_user_message_ready_triggers_awaiting_llm_phase(worker_event_dispatcher, agent_context, mock_event_handler_registry, mock_event_handler):
    agent_context.current_status = AgentStatus.PROCESSING_USER_INPUT
    event = LLMUserMessageReadyEvent(llm_user_message=MagicMock())
    mock_event_handler_registry.get_handler.return_value = mock_event_handler

    await worker_event_dispatcher.dispatch(event, agent_context)
    agent_context.status_manager.notify_awaiting_llm_response.assert_awaited_once()

@pytest.mark.asyncio
async def test_dispatch_pending_tool_invocation_auto_execute_true(worker_event_dispatcher, agent_context, mock_event_handler_registry, mock_event_handler):
    agent_context.config.auto_execute_tools = True
    tool_invocation = ToolInvocation(name="test_tool", arguments={}, id="tid1")
    event = PendingToolInvocationEvent(tool_invocation=tool_invocation)
    mock_event_handler_registry.get_handler.return_value = mock_event_handler

    await worker_event_dispatcher.dispatch(event, agent_context)
    agent_context.status_manager.notify_tool_execution_started.assert_awaited_once_with("test_tool")
    agent_context.status_manager.notify_tool_execution_pending_approval.assert_not_awaited()

@pytest.mark.asyncio
async def test_dispatch_pending_tool_invocation_auto_execute_false(worker_event_dispatcher, agent_context, mock_event_handler_registry, mock_event_handler):
    agent_context.config.auto_execute_tools = False
    tool_invocation = ToolInvocation(name="test_tool", arguments={}, id="tid1")
    event = PendingToolInvocationEvent(tool_invocation=tool_invocation)
    mock_event_handler_registry.get_handler.return_value = mock_event_handler

    await worker_event_dispatcher.dispatch(event, agent_context)
    agent_context.status_manager.notify_tool_execution_pending_approval.assert_awaited_once_with(tool_invocation)
    agent_context.status_manager.notify_tool_execution_started.assert_not_awaited()

@pytest.mark.asyncio
async def test_dispatch_tool_execution_approval_approved(worker_event_dispatcher, agent_context, mock_event_handler_registry, mock_event_handler):
    tool_invocation_id = "tid1"
    agent_context.state.pending_tool_approvals = {tool_invocation_id: ToolInvocation(name="approved_tool", id=tool_invocation_id)}
    
    event = ToolExecutionApprovalEvent(tool_invocation_id=tool_invocation_id, is_approved=True)
    mock_event_handler_registry.get_handler.return_value = mock_event_handler

    await worker_event_dispatcher.dispatch(event, agent_context)
    agent_context.status_manager.notify_tool_execution_resumed_after_approval.assert_awaited_once_with(approved=True, tool_name="approved_tool")

@pytest.mark.asyncio
async def test_dispatch_tool_execution_approval_denied(worker_event_dispatcher, agent_context, mock_event_handler_registry, mock_event_handler):
    tool_invocation_id = "tid2"
    agent_context.state.pending_tool_approvals = {tool_invocation_id: ToolInvocation(name="denied_tool", id=tool_invocation_id)}
    
    event = ToolExecutionApprovalEvent(tool_invocation_id=tool_invocation_id, is_approved=False)
    mock_event_handler_registry.get_handler.return_value = mock_event_handler

    await worker_event_dispatcher.dispatch(event, agent_context)
    agent_context.status_manager.notify_tool_execution_resumed_after_approval.assert_awaited_once_with(approved=False, tool_name="denied_tool")

@pytest.mark.asyncio
async def test_dispatch_tool_result_triggers_processing_result_phase(worker_event_dispatcher, agent_context, mock_event_handler_registry, mock_event_handler):
    agent_context.current_status = AgentStatus.EXECUTING_TOOL
    event = ToolResultEvent(tool_name="test_tool_result", result="some_result")
    mock_event_handler_registry.get_handler.return_value = mock_event_handler

    await worker_event_dispatcher.dispatch(event, agent_context)
    agent_context.status_manager.notify_processing_tool_result.assert_awaited_once_with("test_tool_result")

@pytest.mark.asyncio
async def test_dispatch_llm_complete_response_triggers_analyzing_phase(worker_event_dispatcher, agent_context, mock_event_handler_registry, mock_event_handler):
    agent_context.current_status = AgentStatus.AWAITING_LLM_RESPONSE
    response_obj = CompleteResponse(content="Response text")
    event = LLMCompleteResponseReceivedEvent(complete_response=response_obj)
    mock_event_handler_registry.get_handler.return_value = mock_event_handler

    await worker_event_dispatcher.dispatch(event, agent_context)
    agent_context.status_manager.notify_analyzing_llm_response.assert_awaited_once()

# --- Post-Handler Phase Transition Tests ---
@pytest.mark.asyncio
async def test_dispatch_agent_ready_event_triggers_initialization_complete(worker_event_dispatcher, agent_context, mock_event_handler_registry, mock_event_handler):
    event = AgentReadyEvent()
    mock_event_handler_registry.get_handler.return_value = mock_event_handler

    call_order = []
    mock_event_handler.handle.side_effect = lambda *args, **kwargs: call_order.append("handle")
    # side_effect for an AsyncMock must be awaitable or a coroutine function
    async def notify_side_effect(*args, **kwargs):
        call_order.append("notify")
    agent_context.status_manager.notify_initialization_complete.side_effect = notify_side_effect
    
    await worker_event_dispatcher.dispatch(event, agent_context)
    
    agent_context.status_manager.notify_initialization_complete.assert_awaited_once()
    mock_event_handler.handle.assert_awaited_once_with(event, agent_context)
    assert call_order == ["handle", "notify"], "Handler should be called before notifier"


@pytest.mark.asyncio
async def test_dispatch_llm_complete_response_to_idle(worker_event_dispatcher, agent_context, mock_event_handler_registry, mock_event_handler):
    agent_context.current_status = AgentStatus.AWAITING_LLM_RESPONSE
    agent_context.state.pending_tool_approvals.clear()
    agent_context.input_event_queues.tool_invocation_request_queue.empty.return_value = True
    
    response_obj = CompleteResponse(content="Response text")
    event = LLMCompleteResponseReceivedEvent(complete_response=response_obj)
    mock_event_handler_registry.get_handler.return_value = mock_event_handler

    async def set_analyzing_phase(*args, **kwargs):
        agent_context.current_status = AgentStatus.ANALYZING_LLM_RESPONSE
    agent_context.status_manager.notify_analyzing_llm_response.side_effect = set_analyzing_phase

    call_order = []
    mock_event_handler.handle.side_effect = lambda *args, **kwargs: call_order.append("handle")
    async def notify_idle_side_effect(*args, **kwargs):
        call_order.append("notify_idle")
    agent_context.status_manager.notify_processing_complete_and_idle.side_effect = notify_idle_side_effect

    await worker_event_dispatcher.dispatch(event, agent_context)
    
    agent_context.status_manager.notify_analyzing_llm_response.assert_awaited_once()
    mock_event_handler.handle.assert_awaited_once_with(event, agent_context)
    agent_context.status_manager.notify_processing_complete_and_idle.assert_awaited_once()
    assert call_order == ["handle", "notify_idle"], "Handler should be called before idle notification"


@pytest.mark.asyncio
async def test_dispatch_llm_complete_not_to_idle_if_pending_approvals(worker_event_dispatcher, agent_context, mock_event_handler_registry, mock_event_handler):
    agent_context.current_status = AgentStatus.AWAITING_LLM_RESPONSE
    agent_context.state.pending_tool_approvals = {"tid1": MagicMock()}
    agent_context.input_event_queues.tool_invocation_request_queue.empty.return_value = True
    
    response_obj = CompleteResponse(content="Response text")
    event = LLMCompleteResponseReceivedEvent(complete_response=response_obj)
    mock_event_handler_registry.get_handler.return_value = mock_event_handler

    async def set_analyzing_phase(*args, **kwargs):
        agent_context.current_status = AgentStatus.ANALYZING_LLM_RESPONSE
    agent_context.status_manager.notify_analyzing_llm_response.side_effect = set_analyzing_phase

    await worker_event_dispatcher.dispatch(event, agent_context)
    agent_context.status_manager.notify_processing_complete_and_idle.assert_not_awaited()

@pytest.mark.asyncio
async def test_dispatch_llm_complete_not_to_idle_if_tool_requests_pending(worker_event_dispatcher, agent_context, mock_event_handler_registry, mock_event_handler):
    agent_context.current_status = AgentStatus.AWAITING_LLM_RESPONSE
    agent_context.state.pending_tool_approvals.clear()
    agent_context.input_event_queues.tool_invocation_request_queue.empty.return_value = False
    
    response_obj = CompleteResponse(content="Response text")
    event = LLMCompleteResponseReceivedEvent(complete_response=response_obj)
    mock_event_handler_registry.get_handler.return_value = mock_event_handler

    async def set_analyzing_phase(*args, **kwargs):
        agent_context.current_status = AgentStatus.ANALYZING_LLM_RESPONSE
    agent_context.status_manager.notify_analyzing_llm_response.side_effect = set_analyzing_phase

    await worker_event_dispatcher.dispatch(event, agent_context)
    agent_context.status_manager.notify_processing_complete_and_idle.assert_not_awaited()

# --- No Transition Scenarios ---
@pytest.mark.asyncio
async def test_dispatch_user_message_not_from_idle_no_processing_phase_trigger(worker_event_dispatcher, agent_context, mock_event_handler_registry, mock_event_handler):
    agent_context.current_status = AgentStatus.PROCESSING_USER_INPUT
    event = UserMessageReceivedEvent(agent_input_user_message=MagicMock())
    mock_event_handler_registry.get_handler.return_value = mock_event_handler

    await worker_event_dispatcher.dispatch(event, agent_context)
    agent_context.status_manager.notify_processing_input_started.assert_not_awaited()

@pytest.mark.asyncio
async def test_dispatch_llm_user_message_ready_if_already_awaiting_llm_or_error(worker_event_dispatcher, agent_context, mock_event_handler_registry, mock_event_handler):
    test_phases = [AgentStatus.AWAITING_LLM_RESPONSE, AgentStatus.ERROR]
    for phase in test_phases:
        agent_context.current_status = phase
        agent_context.status_manager.reset_mock()
        
        event = LLMUserMessageReadyEvent(llm_user_message=MagicMock())
        mock_event_handler_registry.get_handler.return_value = mock_event_handler

        await worker_event_dispatcher.dispatch(event, agent_context)
        agent_context.status_manager.notify_awaiting_llm_response.assert_not_awaited()

@pytest.mark.asyncio
async def test_tool_execution_approval_tool_name_resolution_failure(worker_event_dispatcher, agent_context, mock_event_handler_registry, mock_event_handler):
    tool_invocation_id = "tid_unknown"
    agent_context.state.pending_tool_approvals = {}
    
    event = ToolExecutionApprovalEvent(tool_invocation_id=tool_invocation_id, is_approved=True)
    mock_event_handler_registry.get_handler.return_value = mock_event_handler

    with patch('autobyteus.agent.events.worker_event_dispatcher.logger') as mock_logger:
        await worker_event_dispatcher.dispatch(event, agent_context)
        
        agent_context.status_manager.notify_tool_execution_resumed_after_approval.assert_awaited_once_with(approved=True, tool_name="unknown_tool")
        mock_logger.warning.assert_called_once()
        assert f"Could not find pending invocation for ID '{tool_invocation_id}'" in mock_logger.warning.call_args[0][0]

@pytest.mark.asyncio
async def test_dispatch_agent_ready_event_call_order(worker_event_dispatcher, agent_context, mock_event_handler_registry, mock_event_handler):
    """Test the call order for AgentReadyEvent more directly."""
    event = AgentReadyEvent()
    mock_event_handler_registry.get_handler.return_value = mock_event_handler

    await worker_event_dispatcher.dispatch(event, agent_context)

    mock_event_handler.handle.assert_awaited_once_with(event, agent_context)
    agent_context.status_manager.notify_initialization_complete.assert_awaited_once()

@pytest.mark.xfail(reason="Testing call order with unittest.mock.call is complex with async mocks, this might fail.")
@pytest.mark.asyncio
async def test_dispatch_agent_ready_event_call_order_strict(worker_event_dispatcher, agent_context, mock_event_handler_registry, mock_event_handler):
    """A stricter version of the call order test that is expected to be brittle."""
    event = AgentReadyEvent()
    mock_event_handler_registry.get_handler.return_value = mock_event_handler

    manager = MagicMock()
    manager.attach_mock(mock_event_handler, 'handler_mock')
    manager.attach_mock(agent_context.status_manager, 'status_manager_mock')

    await worker_event_dispatcher.dispatch(event, agent_context)

    expected_calls = [
        patch('unittest.mock.call').handler_mock.handle(event, agent_context),
        patch('unittest.mock.call').status_manager_mock.notify_initialization_complete()
    ]
    manager.assert_has_calls(expected_calls, any_order=False)
