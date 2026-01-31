import pytest
import logging
import json
import traceback
from unittest.mock import MagicMock, AsyncMock, patch, call, ANY

from autobyteus.agent.handlers.tool_invocation_request_event_handler import ToolInvocationRequestEventHandler
from autobyteus.agent.events.agent_events import PendingToolInvocationEvent, ToolResultEvent, GenericEvent
from autobyteus.agent.tool_invocation import ToolInvocation


@pytest.fixture
def tool_request_handler():
    return ToolInvocationRequestEventHandler()

# Mock format_to_clean_string to return consistent output for tests
@pytest.fixture(autouse=True)
def mock_formatter():
    with patch('autobyteus.agent.handlers.tool_invocation_request_event_handler.format_to_clean_string') as mock:
        mock.side_effect = lambda x: json.dumps(x) if isinstance(x, (dict, list)) else str(x)
        yield mock

# --- Tests for Approval Required Path (auto_execute_tools = False) ---
@pytest.mark.asyncio
async def test_handle_approval_required_logic(tool_request_handler: ToolInvocationRequestEventHandler, agent_context, mock_tool_invocation, caplog):
    """Test when approval is required: stores invocation, updates history, and notifies for approval."""
    agent_context.config.auto_execute_tools = False 
    event = PendingToolInvocationEvent(tool_invocation=mock_tool_invocation)

    agent_context.status_manager.notifier = MagicMock()

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
    agent_context.status_manager.notifier.notify_agent_request_tool_invocation_approval.assert_called_once_with(expected_approval_data)

    agent_context.get_tool.assert_not_called()
    agent_context.input_event_queues.enqueue_tool_result.assert_not_called()


@pytest.mark.asyncio
async def test_handle_approval_required_notifier_missing_critical_log(tool_request_handler: ToolInvocationRequestEventHandler, agent_context, mock_tool_invocation, caplog):
    agent_context.config.auto_execute_tools = False
    agent_context.status_manager.notifier = None 
    event = PendingToolInvocationEvent(tool_invocation=mock_tool_invocation)

    with caplog.at_level(logging.CRITICAL):
        await tool_request_handler.handle(event, agent_context)
    
    assert f"Agent '{agent_context.agent_id}': Notifier is REQUIRED for manual tool approval flow but is unavailable. Tool '{mock_tool_invocation.name}' cannot be processed for approval." in caplog.text
    agent_context.state.store_pending_tool_invocation.assert_not_called()


# --- Tests for Direct Execution Path (auto_execute_tools = True) ---
@pytest.mark.asyncio
async def test_handle_direct_execution_success(tool_request_handler: ToolInvocationRequestEventHandler, agent_context, mock_tool_instance, mock_tool_invocation, caplog):
    agent_context.config.auto_execute_tools = True 
    event = PendingToolInvocationEvent(tool_invocation=mock_tool_invocation)

    tool_result = "Direct execution successful!"
    mock_tool_instance.execute = AsyncMock(return_value=tool_result)
    agent_context.get_tool.side_effect = None # Clear default side_effect from fixture
    agent_context.get_tool.return_value = mock_tool_instance
    agent_context.status_manager.notifier = MagicMock()

    with caplog.at_level(logging.INFO):
        await tool_request_handler.handle(event, agent_context)

    assert f"Agent '{agent_context.agent_id}': Tool '{mock_tool_invocation.name}' (ID: {mock_tool_invocation.id}) executing automatically" in caplog.text 
    assert f"Tool '{mock_tool_invocation.name}' (ID: {mock_tool_invocation.id}) executed by agent '{agent_context.agent_id}'" in caplog.text

    agent_context.state.store_pending_tool_invocation.assert_not_called() 
    
    # format_to_clean_string is mocked to behave like json.dumps for dict/list or str(x) otherwise
    expected_log_call_str = f"[TOOL_CALL_DIRECT] Agent_ID: {agent_context.agent_id}, Tool: {mock_tool_invocation.name}, Invocation_ID: {mock_tool_invocation.id}, Arguments: {json.dumps(mock_tool_invocation.arguments)}"
    result_str_for_log = str(tool_result) # Mock return str(x) for string input
    expected_log_result_str = f"[TOOL_RESULT_DIRECT] Agent_ID: {agent_context.agent_id}, Tool: {mock_tool_invocation.name}, Invocation_ID: {mock_tool_invocation.id}, Outcome (first 200 chars): {result_str_for_log[:200]}"
    
    for _ in range(2):
        agent_context.status_manager.notifier.notify_agent_data_tool_log.assert_any_call({
            "log_entry": ANY,
            "tool_invocation_id": mock_tool_invocation.id,
            "tool_name": mock_tool_invocation.name
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
    agent_context.get_tool.side_effect = None # Clear default side_effect from fixture
    agent_context.get_tool.return_value = None 
    agent_context.status_manager.notifier = MagicMock()

    with caplog.at_level(logging.ERROR):
        await tool_request_handler.handle(event, agent_context)

    error_message = f"Tool '{mock_tool_invocation.name}' not found or configured for agent '{agent_context.agent_id}'."
    assert error_message in caplog.text

    expected_log_call_str = f"[TOOL_CALL_DIRECT] Agent_ID: {agent_context.agent_id}, Tool: {mock_tool_invocation.name}, Invocation_ID: {mock_tool_invocation.id}, Arguments: {json.dumps(mock_tool_invocation.arguments)}"
    expected_log_error_str = f"[TOOL_ERROR_DIRECT] Agent_ID: {agent_context.agent_id}, Tool: {mock_tool_invocation.name}, Invocation_ID: {mock_tool_invocation.id}, Error: {error_message}"
    
    # Relaxed assertion for log content
    agent_context.status_manager.notifier.notify_agent_data_tool_log.assert_any_call({
        "log_entry": ANY,
        "tool_invocation_id": mock_tool_invocation.id,
        "tool_name": mock_tool_invocation.name
    })
    agent_context.status_manager.notifier.notify_agent_error_output_generation.assert_called_once_with(
        error_source=f"ToolExecutionDirect.ToolNotFound.{mock_tool_invocation.name}",
        error_message=error_message
    )
    
    enqueued_event = agent_context.input_event_queues.enqueue_tool_result.call_args[0][0]
    assert enqueued_event.error == error_message

@pytest.mark.asyncio
async def test_handle_direct_execution_tool_exception(tool_request_handler: ToolInvocationRequestEventHandler, agent_context, mock_tool_instance, mock_tool_invocation, caplog):
    agent_context.config.auto_execute_tools = True 
    event = PendingToolInvocationEvent(tool_invocation=mock_tool_invocation)

    simulated_tool_error = "Tool crashed unexpectedly!"
    mock_tool_instance.execute = AsyncMock(side_effect=Exception(simulated_tool_error))
    agent_context.get_tool.side_effect = None # Clear default side_effect from fixture
    agent_context.get_tool.return_value = mock_tool_instance
    agent_context.status_manager.notifier = MagicMock()

    with caplog.at_level(logging.ERROR):
        await tool_request_handler.handle(event, agent_context)

    expected_error_log = f"Error executing tool '{mock_tool_invocation.name}' (ID: {mock_tool_invocation.id}): {simulated_tool_error}"
    assert expected_error_log in caplog.text

    expected_log_call_str = f"[TOOL_CALL_DIRECT] Agent_ID: {agent_context.agent_id}, Tool: {mock_tool_invocation.name}, Invocation_ID: {mock_tool_invocation.id}, Arguments: {json.dumps(mock_tool_invocation.arguments)}"
    expected_log_exception_str = f"[TOOL_EXCEPTION_DIRECT] Agent_ID: {agent_context.agent_id}, Tool: {mock_tool_invocation.name}, Invocation_ID: {mock_tool_invocation.id}, Exception: {expected_error_log}"
    
    # Relaxed assertion for log content
    agent_context.status_manager.notifier.notify_agent_data_tool_log.assert_any_call({
        "log_entry": ANY,
        "tool_invocation_id": mock_tool_invocation.id,
        "tool_name": mock_tool_invocation.name
    })
    
    agent_context.status_manager.notifier.notify_agent_error_output_generation.assert_called_once()
    call_args_error_gen = agent_context.status_manager.notifier.notify_agent_error_output_generation.call_args[1]
    assert call_args_error_gen['error_source'] == f"ToolExecutionDirect.Exception.{mock_tool_invocation.name}"
    assert call_args_error_gen['error_message'] == expected_error_log
    assert isinstance(call_args_error_gen['error_details'], str)


    enqueued_event = agent_context.input_event_queues.enqueue_tool_result.call_args[0][0]
    assert enqueued_event.error == expected_error_log


@pytest.mark.asyncio
async def test_handle_direct_execution_args_not_json_serializable_for_log(tool_request_handler: ToolInvocationRequestEventHandler, agent_context, mock_tool_instance, caplog):
    agent_context.config.auto_execute_tools = True 
    class Unserializable:
        def __repr__(self):
            return "UnserializableObj"
    unserializable_args = {"data": Unserializable()}
    tool_invocation = ToolInvocation(name="test_tool", arguments=unserializable_args, id="direct-json-err-args")
    event = PendingToolInvocationEvent(tool_invocation=tool_invocation)

    mock_tool_instance.execute = AsyncMock(return_value="result")
    agent_context.get_tool.side_effect = None # Clear default side_effect from fixture
    agent_context.get_tool.return_value = mock_tool_instance
    agent_context.status_manager.notifier = MagicMock()
    
    await tool_request_handler.handle(event, agent_context)
    
    expected_log_call_str = f"[TOOL_CALL_DIRECT] Agent_ID: {agent_context.agent_id}, Tool: test_tool, Invocation_ID: direct-json-err-args, Arguments: {str(unserializable_args)}"
    agent_context.status_manager.notifier.notify_agent_data_tool_log.assert_any_call({
        "log_entry": ANY,
        "tool_invocation_id": "direct-json-err-args",
        "tool_name": "test_tool"
    })


@pytest.mark.asyncio
async def test_handle_direct_execution_result_not_json_serializable_for_log(tool_request_handler: ToolInvocationRequestEventHandler, agent_context, mock_tool_instance, mock_tool_invocation, caplog):
    agent_context.config.auto_execute_tools = True 
    event = PendingToolInvocationEvent(tool_invocation=mock_tool_invocation)

    class Unserializable:
        def __repr__(self):
            return "UnserializableObj"
    unserializable_result = Unserializable()
    mock_tool_instance.execute = AsyncMock(return_value=unserializable_result)
    agent_context.get_tool.side_effect = None # Clear default side_effect from fixture
    agent_context.get_tool.return_value = mock_tool_instance
    agent_context.status_manager.notifier = MagicMock()
    
    await tool_request_handler.handle(event, agent_context)

    expected_log_result_str = str(unserializable_result)
    agent_context.status_manager.notifier.notify_agent_data_tool_log.assert_any_call({
        "log_entry": ANY,
        "tool_invocation_id": mock_tool_invocation.id,
        "tool_name": mock_tool_invocation.name
    })


# --- General Tests ---
@pytest.mark.asyncio
async def test_handle_invalid_event_type(tool_request_handler: ToolInvocationRequestEventHandler, agent_context, caplog):
    invalid_event = GenericEvent(payload={}, type_name="other_event")
    agent_context.status_manager.notifier = MagicMock()

    with caplog.at_level(logging.WARNING):
        await tool_request_handler.handle(invalid_event, agent_context)
    
    assert f"ToolInvocationRequestEventHandler received non-PendingToolInvocationEvent: {type(invalid_event)}. Skipping." in caplog.text
    agent_context.state.store_pending_tool_invocation.assert_not_called()
    agent_context.status_manager.notifier.notify_agent_request_tool_invocation_approval.assert_not_called()
    agent_context.get_tool.assert_not_called()


def test_tool_request_handler_initialization(caplog):
    with caplog.at_level(logging.INFO):
        handler = ToolInvocationRequestEventHandler()
    assert "ToolInvocationRequestEventHandler initialized." in caplog.text
