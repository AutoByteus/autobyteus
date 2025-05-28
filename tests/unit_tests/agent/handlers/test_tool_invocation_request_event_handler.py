import pytest
import logging
import json
from unittest.mock import MagicMock, AsyncMock, patch, call

# UPDATED IMPORT: TOOL_APPROVAL_REQUESTED_EVENT_TYPE removed
from autobyteus.agent.handlers.tool_invocation_request_event_handler import ToolInvocationRequestEventHandler
from autobyteus.agent.events.agent_events import PendingToolInvocationEvent, ToolResultEvent, GenericEvent
from autobyteus.agent.tool_invocation import ToolInvocation


@pytest.fixture
def tool_request_handler():
    return ToolInvocationRequestEventHandler()

# --- Tests for Approval Required Path (auto_execute_tools = False) ---
@pytest.mark.asyncio
# RENAMED Test
async def test_handle_approval_required_stores_invocation_and_updates_history(tool_request_handler: ToolInvocationRequestEventHandler, agent_context, mock_tool_invocation, caplog):
    """Test when approval is required: stores invocation and updates history."""
    # CORRECTED: Set auto_execute_tools on the config object within the context
    agent_context.config.auto_execute_tools = False # CRITICAL: Set for approval path
    event = PendingToolInvocationEvent(tool_invocation=mock_tool_invocation)

    with caplog.at_level(logging.DEBUG): # Capture DEBUG for the new log message
        await tool_request_handler.handle(event, agent_context)

    # Check logs
    assert f"Agent '{agent_context.agent_id}': Tool '{mock_tool_invocation.name}' (ID: {mock_tool_invocation.id}) requires approval. Storing pending invocation." in caplog.text
    # REMOVED: assert f"Emitted '{TOOL_APPROVAL_REQUESTED_EVENT_TYPE}' for tool '{mock_tool_invocation.name}' (ID: {mock_tool_invocation.id})." in caplog.text
    assert f"Agent '{agent_context.agent_id}': Added assistant tool_calls to history for pending approval of '{mock_tool_invocation.name}' (ID: {mock_tool_invocation.id}). External event emission for approval request is no longer handled here." in caplog.text
    
    # Check context interactions
    agent_context.store_pending_tool_invocation.assert_called_once_with(mock_tool_invocation)
    
    # REMOVED: Check event emission through context.status_manager.emitter
    agent_context.status_manager.emitter.emit.assert_not_called()

    # Check history update (assistant tool_calls message)
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
    agent_context.add_message_to_history.assert_called_once_with(expected_history_tool_call)

    # Ensure tool was NOT executed directly and no ToolResultEvent was enqueued by THIS handler
    agent_context.get_tool.assert_not_called()
    agent_context.queues.enqueue_tool_result.assert_not_called()


# REMOVED test_handle_approval_required_emitter_missing as emitter is no longer used by handler
# REMOVED test_handle_approval_required_emitter_raises_exception as emitter is no longer used by handler


@pytest.mark.asyncio
async def test_handle_approval_required_arguments_not_json_serializable(tool_request_handler: ToolInvocationRequestEventHandler, agent_context, caplog):
    """Test approval path when tool arguments are not JSON serializable for history."""
    agent_context.config.auto_execute_tools = False # CORRECTED
    
    unserializable_args = {"data": set([1,2,3])} 
    tool_invocation_bad_args = ToolInvocation(name="test_tool", arguments=unserializable_args, id="bad-args-id")
    event = PendingToolInvocationEvent(tool_invocation=tool_invocation_bad_args)

    with caplog.at_level(logging.WARNING): 
        await tool_request_handler.handle(event, agent_context)

    assert "Could not serialize arguments for tool_call history message for tool 'test_tool'" in caplog.text
    
    expected_history_tool_call = {
        "role": "assistant",
        "content": None,
        "tool_calls": [{
            "id": "bad-args-id",
            "type": "function",
            "function": {"name": "test_tool", "arguments": "{}"} 
        }]
    }
    agent_context.add_message_to_history.assert_called_once_with(expected_history_tool_call)
    agent_context.store_pending_tool_invocation.assert_called_once_with(tool_invocation_bad_args)


# --- Tests for Direct Execution Path (auto_execute_tools = True) ---
@pytest.mark.asyncio
async def test_handle_direct_execution_success(tool_request_handler: ToolInvocationRequestEventHandler, agent_context, mock_tool_instance, mock_tool_invocation, caplog):
    """Test direct tool execution when auto_execute_tools is True."""
    agent_context.config.auto_execute_tools = True # Ensure it's True for this path
    event = PendingToolInvocationEvent(tool_invocation=mock_tool_invocation)

    tool_result = "Direct execution successful!"
    mock_tool_instance.execute = AsyncMock(return_value=tool_result)
    agent_context.get_tool = MagicMock(return_value=mock_tool_instance)


    with caplog.at_level(logging.INFO):
        await tool_request_handler.handle(event, agent_context)

    # Check logs
    assert f"Agent '{agent_context.agent_id}': Tool '{mock_tool_invocation.name}' (ID: {mock_tool_invocation.id}) exec auto (auto_execute_tools=True)." in caplog.text 
    assert f"Tool '{mock_tool_invocation.name}' (ID: {mock_tool_invocation.id}) executed successfully by agent '{agent_context.agent_id}'" in caplog.text

    # Check context interactions for direct execution
    agent_context.store_pending_tool_invocation.assert_not_called() 
    agent_context.status_manager.emitter.emit.assert_not_called()   

    # Check tool log queue entries
    expected_log_call = f"[TOOL_CALL_DIRECT] Agent_ID: {agent_context.agent_id}, Tool: {mock_tool_invocation.name}, Invocation_ID: {mock_tool_invocation.id}, Arguments: {json.dumps(mock_tool_invocation.arguments)}"
    expected_log_result_part = f"[TOOL_RESULT_DIRECT] Agent_ID: {agent_context.agent_id}, Tool: {mock_tool_invocation.name}, Invocation_ID: {mock_tool_invocation.id}, Outcome (first 200 chars): {str(tool_result)[:200]}"
    
    put_calls = [args[0][0] for args in agent_context.queues.tool_interaction_log_queue.put.call_args_list]
    assert expected_log_call in put_calls
    assert any(c.startswith(expected_log_result_part) for c in put_calls)

    # Check history update (tool role with result)
    agent_context.add_message_to_history.assert_called_once_with({
        "role": "tool",
        "tool_call_id": mock_tool_invocation.id,
        "name": mock_tool_invocation.name,
        "content": str(tool_result),
    })

    # Check enqueued ToolResultEvent
    agent_context.queues.enqueue_tool_result.assert_called_once()
    enqueued_event = agent_context.queues.enqueue_tool_result.call_args[0][0]
    assert isinstance(enqueued_event, ToolResultEvent)
    assert enqueued_event.tool_name == mock_tool_invocation.name
    assert enqueued_event.result == tool_result
    assert enqueued_event.error is None
    assert enqueued_event.tool_invocation_id == mock_tool_invocation.id

    # Verify tool's execute method was called correctly
    mock_tool_instance.execute.assert_called_once_with(context=agent_context, **mock_tool_invocation.arguments)


@pytest.mark.asyncio
async def test_handle_direct_execution_tool_not_found(tool_request_handler: ToolInvocationRequestEventHandler, agent_context, mock_tool_invocation, caplog):
    """Test direct execution when tool is not found."""
    agent_context.config.auto_execute_tools = True # CORRECTED
    event = PendingToolInvocationEvent(tool_invocation=mock_tool_invocation)

    agent_context.get_tool = MagicMock(return_value=None) 

    with caplog.at_level(logging.ERROR):
        await tool_request_handler.handle(event, agent_context)

    error_message = f"Tool '{mock_tool_invocation.name}' not found or configured for agent '{agent_context.agent_id}'."
    assert error_message in caplog.text

    # Check tool log queue for call and error
    expected_log_call = f"[TOOL_CALL_DIRECT] Agent_ID: {agent_context.agent_id}, Tool: {mock_tool_invocation.name}, Invocation_ID: {mock_tool_invocation.id}, Arguments: {json.dumps(mock_tool_invocation.arguments)}"
    expected_log_error = f"[TOOL_ERROR_DIRECT] Agent_ID: {agent_context.agent_id}, Tool: {mock_tool_invocation.name}, Invocation_ID: {mock_tool_invocation.id}, Error: {error_message}"
    
    put_calls = [args[0][0] for args in agent_context.queues.tool_interaction_log_queue.put.call_args_list]
    assert expected_log_call in put_calls
    assert expected_log_error in put_calls
    
    # Check history
    agent_context.add_message_to_history.assert_called_once_with({
        "role": "tool", "tool_call_id": mock_tool_invocation.id, "name": mock_tool_invocation.name,
        "content": f"Error: Tool '{mock_tool_invocation.name}' execution failed. Reason: {error_message}"
    })
    # Check enqueued error ToolResultEvent
    enqueued_event = agent_context.queues.enqueue_tool_result.call_args[0][0]
    assert enqueued_event.error == error_message

@pytest.mark.asyncio
async def test_handle_direct_execution_tool_exception(tool_request_handler: ToolInvocationRequestEventHandler, agent_context, mock_tool_instance, mock_tool_invocation, caplog):
    """Test direct execution when tool.execute() raises an exception."""
    agent_context.config.auto_execute_tools = True # CORRECTED
    event = PendingToolInvocationEvent(tool_invocation=mock_tool_invocation)

    simulated_tool_error = "Tool crashed unexpectedly!"
    mock_tool_instance.execute = AsyncMock(side_effect=Exception(simulated_tool_error))
    agent_context.get_tool = MagicMock(return_value=mock_tool_instance)

    with caplog.at_level(logging.ERROR):
        await tool_request_handler.handle(event, agent_context)

    expected_error_log = f"Error executing tool '{mock_tool_invocation.name}' (ID: {mock_tool_invocation.id}): {simulated_tool_error}"
    assert expected_error_log in caplog.text

    # Check tool log queue for call and exception
    expected_log_call = f"[TOOL_CALL_DIRECT] Agent_ID: {agent_context.agent_id}, Tool: {mock_tool_invocation.name}, Invocation_ID: {mock_tool_invocation.id}, Arguments: {json.dumps(mock_tool_invocation.arguments)}"
    expected_log_exception = f"[TOOL_EXCEPTION_DIRECT] Agent_ID: {agent_context.agent_id}, Tool: {mock_tool_invocation.name}, Invocation_ID: {mock_tool_invocation.id}, Exception: {expected_error_log}"
    
    put_calls = [args[0][0] for args in agent_context.queues.tool_interaction_log_queue.put.call_args_list]
    assert expected_log_call in put_calls
    assert expected_log_exception in put_calls

    # Check history
    agent_context.add_message_to_history.assert_called_once_with({
        "role": "tool", "tool_call_id": mock_tool_invocation.id, "name": mock_tool_invocation.name,
        "content": f"Error: Tool '{mock_tool_invocation.name}' execution failed. Reason: {expected_error_log}"
    })
    # Check enqueued error ToolResultEvent
    enqueued_event = agent_context.queues.enqueue_tool_result.call_args[0][0]
    assert enqueued_event.error == expected_error_log


@pytest.mark.asyncio
async def test_handle_direct_execution_args_not_json_serializable_for_log(tool_request_handler: ToolInvocationRequestEventHandler, agent_context, mock_tool_instance, caplog):
    agent_context.config.auto_execute_tools = True # CORRECTED
    unserializable_args = {"data": set([1,2,3])}
    tool_invocation = ToolInvocation(name="test_tool", arguments=unserializable_args, id="direct-json-err-args")
    event = PendingToolInvocationEvent(tool_invocation=tool_invocation)

    mock_tool_instance.execute = AsyncMock(return_value="result")
    agent_context.get_tool = MagicMock(return_value=mock_tool_instance)

    await tool_request_handler.handle(event, agent_context)
    
    expected_log_call_str_args = f"[TOOL_CALL_DIRECT] Agent_ID: {agent_context.agent_id}, Tool: test_tool, Invocation_ID: direct-json-err-args, Arguments: {str(unserializable_args)}"
    put_calls = [args[0][0] for args in agent_context.queues.tool_interaction_log_queue.put.call_args_list]
    assert expected_log_call_str_args in put_calls


@pytest.mark.asyncio
async def test_handle_direct_execution_result_not_json_serializable_for_log(tool_request_handler: ToolInvocationRequestEventHandler, agent_context, mock_tool_instance, mock_tool_invocation, caplog):
    agent_context.config.auto_execute_tools = True # CORRECTED
    event = PendingToolInvocationEvent(tool_invocation=mock_tool_invocation)

    unserializable_result = set([1,2,3])
    mock_tool_instance.execute = AsyncMock(return_value=unserializable_result)
    agent_context.get_tool = MagicMock(return_value=mock_tool_instance)
    
    await tool_request_handler.handle(event, agent_context)

    expected_log_result_str = f"[TOOL_RESULT_DIRECT] Agent_ID: {agent_context.agent_id}, Tool: {mock_tool_invocation.name}, Invocation_ID: {mock_tool_invocation.id}, Outcome (first 200 chars): {str(unserializable_result)[:200]}"
    put_calls = [args[0][0] for args in agent_context.queues.tool_interaction_log_queue.put.call_args_list]
    assert any(c.startswith(expected_log_result_str) for c in put_calls)


# --- General Tests ---
@pytest.mark.asyncio
async def test_handle_invalid_event_type(tool_request_handler: ToolInvocationRequestEventHandler, agent_context, caplog):
    """Test that the handler skips events that are not PendingToolInvocationEvent."""
    invalid_event = GenericEvent(payload={}, type_name="other_event")

    with caplog.at_level(logging.WARNING):
        await tool_request_handler.handle(invalid_event, agent_context) # type: ignore
    
    assert f"ToolInvocationRequestEventHandler received non-PendingToolInvocationEvent: {type(invalid_event)}. Skipping." in caplog.text
    # Ensure no core logic was triggered
    agent_context.store_pending_tool_invocation.assert_not_called()
    agent_context.status_manager.emitter.emit.assert_not_called()
    agent_context.get_tool.assert_not_called()


def test_tool_request_handler_initialization(caplog):
    with caplog.at_level(logging.INFO):
        handler = ToolInvocationRequestEventHandler()
    assert "ToolInvocationRequestEventHandler initialized." in caplog.text

