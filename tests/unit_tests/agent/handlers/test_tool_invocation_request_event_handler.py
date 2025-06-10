import pytest
import logging
import json
import traceback
from unittest.mock import MagicMock, AsyncMock, patch, call

from autobyteus.agent.handlers.tool_invocation_request_event_handler import ToolInvocationRequestEventHandler
from autobyteus.agent.events.agent_events import PendingToolInvocationEvent, ToolResultEvent, GenericEvent
from autobyteus.agent.tool_invocation import ToolInvocation


@pytest.fixture
def tool_request_handler():
    return ToolInvocationRequestEventHandler()

# --- Tests for Approval Required Path (auto_execute_tools = False) ---
@pytest.mark.asyncio
async def test_handle_approval_required_logic(tool_request_handler: ToolInvocationRequestEventHandler, agent_context, mock_tool_invocation, caplog):
    """Test when approval is required: stores invocation, updates history, and notifies for approval."""
    agent_context.config.auto_execute_tools = False 
    event = PendingToolInvocationEvent(tool_invocation=mock_tool_invocation)

    agent_context.phase_manager.notifier = AsyncMock()

    with caplog.at_level(logging.DEBUG): 
        await tool_request_handler.handle(event, agent_context)

    assert f"Agent '{agent_context.agent_id}': Tool '{mock_tool_invocation.name}' (ID: {mock_tool_invocation.id}) requires approval." in caplog.text
    assert f"Emitted AGENT_REQUEST_TOOL_INVOCATION_APPROVAL for '{mock_tool_invocation.name}'" in caplog.text
    
    agent_context.state.store_pending_tool_invocation.assert_called_once_with(mock_tool_invocation)
    
    expected_approval_data = {
        "invocation_id": mock_tool_invocation.id,
        "tool_name": mock_tool_invocation.name,
        "arguments": mock_tool_invocation.arguments,
    }
    agent_context.phase_manager.notifier.notify_agent_request_tool_invocation_approval.assert_called_once_with(expected_approval_data)

    expected_history_tool_call = {
        "role": "assistant",
        "content": None,
        "tool_calls": [{
            "id": mock_tool_invocation.id,
            "type": "function",
            "function": {
                "name": mock_tool_invocation.name,
                "arguments": json.dumps(mock_tool_invocation.arguments or {})
            }
        }]
    }
    agent_context.state.add_message_to_history.assert_called_once_with(expected_history_tool_call)

    agent_context.get_tool.assert_not_called()
    agent_context.input_event_queues.enqueue_tool_result.assert_not_called()


@pytest.mark.asyncio
async def test_handle_approval_required_notifier_missing_critical_log(tool_request_handler: ToolInvocationRequestEventHandler, agent_context, mock_tool_invocation, caplog):
    agent_context.config.auto_execute_tools = False
    agent_context.phase_manager.notifier = None 
    event = PendingToolInvocationEvent(tool_invocation=mock_tool_invocation)

    with caplog.at_level(logging.CRITICAL):
        await tool_request_handler.handle(event, agent_context)
    
    assert f"Agent '{agent_context.agent_id}': Notifier is REQUIRED for manual tool approval flow but is unavailable. Tool '{mock_tool_invocation.name}' cannot be processed for approval." in caplog.text
    agent_context.state.store_pending_tool_invocation.assert_not_called()
    agent_context.state.add_message_to_history.assert_not_called()


@pytest.mark.asyncio
async def test_handle_approval_required_arguments_not_json_serializable(tool_request_handler: ToolInvocationRequestEventHandler, agent_context, caplog):
    agent_context.config.auto_execute_tools = False 
    
    unserializable_args = {"data": set([1,2,3])} 
    tool_invocation_bad_args = ToolInvocation(name="test_tool", arguments=unserializable_args, id="bad-args-id")
    event = PendingToolInvocationEvent(tool_invocation=tool_invocation_bad_args)

    agent_context.phase_manager.notifier = AsyncMock()

    with caplog.at_level(logging.WARNING): 
        await tool_request_handler.handle(event, agent_context)

    assert "Could not serialize args for history tool_call for 'test_tool'." in caplog.text
    
    expected_history_tool_call = {
        "role": "assistant",
        "content": None,
        "tool_calls": [{
            "id": "bad-args-id",
            "type": "function",
            "function": {"name": "test_tool", "arguments": "{}"} 
        }]
    }
    agent_context.state.add_message_to_history.assert_called_once_with(expected_history_tool_call)
    agent_context.state.store_pending_tool_invocation.assert_called_once_with(tool_invocation_bad_args)
    agent_context.phase_manager.notifier.notify_agent_request_tool_invocation_approval.assert_called_once()


# --- Tests for Direct Execution Path (auto_execute_tools = True) ---
@pytest.mark.asyncio
async def test_handle_direct_execution_success(tool_request_handler: ToolInvocationRequestEventHandler, agent_context, mock_tool_instance, mock_tool_invocation, caplog):
    agent_context.config.auto_execute_tools = True 
    event = PendingToolInvocationEvent(tool_invocation=mock_tool_invocation)

    tool_result = "Direct execution successful!"
    mock_tool_instance.execute = AsyncMock(return_value=tool_result)
    agent_context.get_tool.return_value = mock_tool_instance
    agent_context.phase_manager.notifier = AsyncMock()

    with caplog.at_level(logging.INFO):
        await tool_request_handler.handle(event, agent_context)

    assert f"Agent '{agent_context.agent_id}': Tool '{mock_tool_invocation.name}' (ID: {mock_tool_invocation.id}) executing automatically" in caplog.text 
    assert f"Tool '{mock_tool_invocation.name}' (ID: {mock_tool_invocation.id}) executed by agent '{agent_context.agent_id}'" in caplog.text

    agent_context.state.store_pending_tool_invocation.assert_not_called() 
    
    expected_log_call_str = f"[TOOL_CALL_DIRECT] Agent_ID: {agent_context.agent_id}, Tool: {mock_tool_invocation.name}, Invocation_ID: {mock_tool_invocation.id}, Arguments: {json.dumps(mock_tool_invocation.arguments)}"
    result_str_for_log = json.dumps(tool_result)
    expected_log_result_str = f"[TOOL_RESULT_DIRECT] Agent_ID: {agent_context.agent_id}, Tool: {mock_tool_invocation.name}, Invocation_ID: {mock_tool_invocation.id}, Outcome (first 200 chars): {result_str_for_log[:200]}"
    
    agent_context.phase_manager.notifier.notify_agent_data_tool_log.assert_any_call(expected_log_call_str)
    agent_context.phase_manager.notifier.notify_agent_data_tool_log.assert_any_call(expected_log_result_str)

    agent_context.state.add_message_to_history.assert_called_once_with({
        "role": "tool",
        "tool_call_id": mock_tool_invocation.id,
        "name": mock_tool_invocation.name,
        "content": str(tool_result),
    })

    agent_context.input_event_queues.enqueue_tool_result.assert_called_once()
    enqueued_event = agent_context.input_event_queues.enqueue_tool_result.call_args[0][0]
    assert isinstance(enqueued_event, ToolResultEvent)
    assert enqueued_event.tool_name == mock_tool_invocation.name
    assert enqueued_event.result == tool_result
    assert enqueued_event.error is None
    assert enqueued_event.tool_invocation_id == mock_tool_invocation.id

    mock_tool_instance.execute.assert_called_once_with(context=agent_context, **mock_tool_invocation.arguments)


@pytest.mark.asyncio
async def test_handle_direct_execution_tool_not_found(tool_request_handler: ToolInvocationRequestEventHandler, agent_context, mock_tool_invocation, caplog):
    agent_context.config.auto_execute_tools = True 
    event = PendingToolInvocationEvent(tool_invocation=mock_tool_invocation)
    agent_context.get_tool.return_value = None 
    agent_context.phase_manager.notifier = AsyncMock()

    with caplog.at_level(logging.ERROR):
        await tool_request_handler.handle(event, agent_context)

    error_message = f"Tool '{mock_tool_invocation.name}' not found or configured for agent '{agent_context.agent_id}'."
    assert error_message in caplog.text

    expected_log_call_str = f"[TOOL_CALL_DIRECT] Agent_ID: {agent_context.agent_id}, Tool: {mock_tool_invocation.name}, Invocation_ID: {mock_tool_invocation.id}, Arguments: {json.dumps(mock_tool_invocation.arguments)}"
    expected_log_error_str = f"[TOOL_ERROR_DIRECT] Agent_ID: {agent_context.agent_id}, Tool: {mock_tool_invocation.name}, Invocation_ID: {mock_tool_invocation.id}, Error: {error_message}"
    
    agent_context.phase_manager.notifier.notify_agent_data_tool_log.assert_any_call(expected_log_call_str)
    agent_context.phase_manager.notifier.notify_agent_data_tool_log.assert_any_call(expected_log_error_str)
    agent_context.phase_manager.notifier.notify_agent_error_output_generation.assert_called_once_with(
        error_source=f"ToolExecutionDirect.ToolNotFound.{mock_tool_invocation.name}",
        error_message=error_message
    )
    
    agent_context.state.add_message_to_history.assert_called_once_with({
        "role": "tool", "tool_call_id": mock_tool_invocation.id, "name": mock_tool_invocation.name,
        "content": f"Error: Tool '{mock_tool_invocation.name}' execution failed. Reason: {error_message}"
    })
    enqueued_event = agent_context.input_event_queues.enqueue_tool_result.call_args[0][0]
    assert enqueued_event.error == error_message

@pytest.mark.asyncio
async def test_handle_direct_execution_tool_exception(tool_request_handler: ToolInvocationRequestEventHandler, agent_context, mock_tool_instance, mock_tool_invocation, caplog):
    agent_context.config.auto_execute_tools = True 
    event = PendingToolInvocationEvent(tool_invocation=mock_tool_invocation)

    simulated_tool_error = "Tool crashed unexpectedly!"
    mock_tool_instance.execute = AsyncMock(side_effect=Exception(simulated_tool_error))
    agent_context.get_tool.return_value = mock_tool_instance
    agent_context.phase_manager.notifier = AsyncMock()

    with caplog.at_level(logging.ERROR):
        await tool_request_handler.handle(event, agent_context)

    expected_error_log = f"Error executing tool '{mock_tool_invocation.name}' (ID: {mock_tool_invocation.id}): {simulated_tool_error}"
    assert expected_error_log in caplog.text

    expected_log_call_str = f"[TOOL_CALL_DIRECT] Agent_ID: {agent_context.agent_id}, Tool: {mock_tool_invocation.name}, Invocation_ID: {mock_tool_invocation.id}, Arguments: {json.dumps(mock_tool_invocation.arguments)}"
    expected_log_exception_str = f"[TOOL_EXCEPTION_DIRECT] Agent_ID: {agent_context.agent_id}, Tool: {mock_tool_invocation.name}, Invocation_ID: {mock_tool_invocation.id}, Exception: {expected_error_log}"
    
    agent_context.phase_manager.notifier.notify_agent_data_tool_log.assert_any_call(expected_log_call_str)
    agent_context.phase_manager.notifier.notify_agent_data_tool_log.assert_any_call(expected_log_exception_str)
    
    agent_context.phase_manager.notifier.notify_agent_error_output_generation.assert_called_once()
    call_args_error_gen = agent_context.phase_manager.notifier.notify_agent_error_output_generation.call_args[1]
    assert call_args_error_gen['error_source'] == f"ToolExecutionDirect.Exception.{mock_tool_invocation.name}"
    assert call_args_error_gen['error_message'] == expected_error_log
    assert isinstance(call_args_error_gen['error_details'], str)


    agent_context.state.add_message_to_history.assert_called_once_with({
        "role": "tool", "tool_call_id": mock_tool_invocation.id, "name": mock_tool_invocation.name,
        "content": f"Error: Tool '{mock_tool_invocation.name}' execution failed. Reason: {expected_error_log}"
    })
    enqueued_event = agent_context.input_event_queues.enqueue_tool_result.call_args[0][0]
    assert enqueued_event.error == expected_error_log


@pytest.mark.asyncio
async def test_handle_direct_execution_args_not_json_serializable_for_log(tool_request_handler: ToolInvocationRequestEventHandler, agent_context, mock_tool_instance, caplog):
    agent_context.config.auto_execute_tools = True 
    unserializable_args = {"data": set([1,2,3])}
    tool_invocation = ToolInvocation(name="test_tool", arguments=unserializable_args, id="direct-json-err-args")
    event = PendingToolInvocationEvent(tool_invocation=tool_invocation)

    mock_tool_instance.execute = AsyncMock(return_value="result")
    agent_context.get_tool.return_value = mock_tool_instance
    agent_context.phase_manager.notifier = AsyncMock()
    
    await tool_request_handler.handle(event, agent_context)
    
    expected_log_call_str = f"[TOOL_CALL_DIRECT] Agent_ID: {agent_context.agent_id}, Tool: test_tool, Invocation_ID: direct-json-err-args, Arguments: {str(unserializable_args)}"
    agent_context.phase_manager.notifier.notify_agent_data_tool_log.assert_any_call(expected_log_call_str)


@pytest.mark.asyncio
async def test_handle_direct_execution_result_not_json_serializable_for_log(tool_request_handler: ToolInvocationRequestEventHandler, agent_context, mock_tool_instance, mock_tool_invocation, caplog):
    agent_context.config.auto_execute_tools = True 
    event = PendingToolInvocationEvent(tool_invocation=mock_tool_invocation)

    unserializable_result = set([1,2,3])
    mock_tool_instance.execute = AsyncMock(return_value=unserializable_result)
    agent_context.get_tool.return_value = mock_tool_instance
    agent_context.phase_manager.notifier = AsyncMock()
    
    await tool_request_handler.handle(event, agent_context)

    expected_log_result_str = f"[TOOL_RESULT_DIRECT] Agent_ID: {agent_context.agent_id}, Tool: {mock_tool_invocation.name}, Invocation_ID: {mock_tool_invocation.id}, Outcome (first 200 chars): {str(unserializable_result)[:200]}"
    agent_context.phase_manager.notifier.notify_agent_data_tool_log.assert_any_call(expected_log_result_str)


# --- General Tests ---
@pytest.mark.asyncio
async def test_handle_invalid_event_type(tool_request_handler: ToolInvocationRequestEventHandler, agent_context, caplog):
    invalid_event = GenericEvent(payload={}, type_name="other_event")
    agent_context.phase_manager.notifier = AsyncMock()

    with caplog.at_level(logging.WARNING):
        await tool_request_handler.handle(invalid_event, agent_context)
    
    assert f"ToolInvocationRequestEventHandler received non-PendingToolInvocationEvent: {type(invalid_event)}. Skipping." in caplog.text
    agent_context.state.store_pending_tool_invocation.assert_not_called()
    agent_context.phase_manager.notifier.notify_agent_request_tool_invocation_approval.assert_not_called()
    agent_context.get_tool.assert_not_called()


def test_tool_request_handler_initialization(caplog):
    with caplog.at_level(logging.INFO):
        handler = ToolInvocationRequestEventHandler()
    assert "ToolInvocationRequestEventHandler initialized." in caplog.text
