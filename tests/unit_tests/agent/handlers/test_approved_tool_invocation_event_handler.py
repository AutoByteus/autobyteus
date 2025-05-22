import pytest
import logging
import json
from unittest.mock import MagicMock, AsyncMock, patch

from autobyteus.agent.handlers.approved_tool_invocation_event_handler import ApprovedToolInvocationEventHandler
from autobyteus.agent.events.agent_events import ApprovedToolInvocationEvent, ToolResultEvent, GenericEvent
from autobyteus.agent.tool_invocation import ToolInvocation


@pytest.fixture
def approved_tool_handler():
    return ApprovedToolInvocationEventHandler()

@pytest.mark.asyncio
async def test_handle_approved_tool_invocation_success(approved_tool_handler: ApprovedToolInvocationEventHandler, agent_context, mock_tool_instance, caplog):
    """Test successful execution of an approved tool."""
    tool_name = "mock_tool"
    tool_args = {"param1": "value1"}
    tool_invocation_id = "approved-tool-id-123"
    
    tool_invocation = ToolInvocation(name=tool_name, arguments=tool_args, id=tool_invocation_id)
    event = ApprovedToolInvocationEvent(tool_invocation=tool_invocation)

    # Setup mock_tool_instance for this specific test
    mock_tool_instance.execute = AsyncMock(return_value="Successful execution result")
    agent_context.tool_instances[tool_name] = mock_tool_instance # Ensure it's in context

    with caplog.at_level(logging.INFO):
        await approved_tool_handler.handle(event, agent_context)

    # Check logs
    assert f"Agent '{agent_context.agent_id}' handling ApprovedToolInvocationEvent for tool: '{tool_name}' (ID: {tool_invocation_id})" in caplog.text
    assert f"Approved tool '{tool_name}' (ID: {tool_invocation_id}) executed successfully by agent '{agent_context.agent_id}'" in caplog.text

    # Check tool log queue
    expected_log_call = f"[APPROVED_TOOL_CALL] Agent_ID: {agent_context.agent_id}, Tool: {tool_name}, Invocation_ID: {tool_invocation_id}, Arguments: {json.dumps(tool_args)}"
    expected_log_result_part = f"[APPROVED_TOOL_RESULT] Agent_ID: {agent_context.agent_id}, Tool: {tool_name}, Invocation_ID: {tool_invocation_id}, Outcome (first 200 chars): "
    
    # Need to check calls on the queue mock
    put_calls = [args[0][0] for args in agent_context.queues.tool_interaction_log_queue.put.call_args_list]
    assert expected_log_call in put_calls
    assert any(c.startswith(expected_log_result_part) for c in put_calls)


    # Check history update
    agent_context.add_message_to_history.assert_called_once_with({
        "role": "tool",
        "tool_call_id": tool_invocation_id,
        "name": tool_name,
        "content": "Successful execution result",
    })

    # Check enqueued ToolResultEvent
    agent_context.queues.enqueue_tool_result.assert_called_once()
    enqueued_event = agent_context.queues.enqueue_tool_result.call_args[0][0]
    assert isinstance(enqueued_event, ToolResultEvent)
    assert enqueued_event.tool_name == tool_name
    assert enqueued_event.result == "Successful execution result"
    assert enqueued_event.error is None
    assert enqueued_event.tool_invocation_id == tool_invocation_id

    # Verify tool's execute method was called correctly
    # Ensure AgentContext is passed to tool.execute
    mock_tool_instance.execute.assert_called_once_with(agent_context, **tool_args)


@pytest.mark.asyncio
async def test_handle_approved_tool_not_found(approved_tool_handler: ApprovedToolInvocationEventHandler, agent_context, caplog):
    """Test handling when the specified tool is not found in the agent's context."""
    tool_name = "non_existent_tool"
    tool_args = {"param": "val"}
    tool_invocation_id = "notfound-tool-id-456"
    
    tool_invocation = ToolInvocation(name=tool_name, arguments=tool_args, id=tool_invocation_id)
    event = ApprovedToolInvocationEvent(tool_invocation=tool_invocation)

    # Ensure the tool is NOT in context.tool_instances
    if tool_name in agent_context.tool_instances: # pragma: no cover
        del agent_context.tool_instances[tool_name]
    agent_context.get_tool = MagicMock(return_value=None) # More robust mocking

    with caplog.at_level(logging.ERROR): # Error is logged for tool not found
        await approved_tool_handler.handle(event, agent_context)

    error_message = f"Tool '{tool_name}' not found or configured for agent '{agent_context.agent_id}'."
    assert error_message in caplog.text

    # Check tool log queue
    expected_log_call = f"[APPROVED_TOOL_CALL] Agent_ID: {agent_context.agent_id}, Tool: {tool_name}, Invocation_ID: {tool_invocation_id}, Arguments: {json.dumps(tool_args)}"
    expected_log_error = f"[APPROVED_TOOL_ERROR] Agent_ID: {agent_context.agent_id}, Tool: {tool_name}, Invocation_ID: {tool_invocation_id}, Error: {error_message}"
    
    put_calls = [args[0][0] for args in agent_context.queues.tool_interaction_log_queue.put.call_args_list]
    assert expected_log_call in put_calls
    assert expected_log_error in put_calls


    # Check history update (error message)
    agent_context.add_message_to_history.assert_called_once_with({
        "role": "tool",
        "tool_call_id": tool_invocation_id,
        "name": tool_name,
        "content": f"Error: Approved tool '{tool_name}' execution failed. Reason: {error_message}",
    })

    # Check enqueued ToolResultEvent (with error)
    agent_context.queues.enqueue_tool_result.assert_called_once()
    enqueued_event = agent_context.queues.enqueue_tool_result.call_args[0][0]
    assert isinstance(enqueued_event, ToolResultEvent)
    assert enqueued_event.tool_name == tool_name
    assert enqueued_event.result is None
    assert enqueued_event.error == error_message
    assert enqueued_event.tool_invocation_id == tool_invocation_id


@pytest.mark.asyncio
async def test_handle_approved_tool_execution_exception(approved_tool_handler: ApprovedToolInvocationEventHandler, agent_context, mock_tool_instance, caplog):
    """Test handling when tool execution raises an exception."""
    tool_name = "failing_tool"
    tool_args = {}
    tool_invocation_id = "fail-tool-id-789"
    
    tool_invocation = ToolInvocation(name=tool_name, arguments=tool_args, id=tool_invocation_id)
    event = ApprovedToolInvocationEvent(tool_invocation=tool_invocation)

    exception_message = "Simulated tool execution failure!"
    mock_tool_instance.execute = AsyncMock(side_effect=Exception(exception_message))
    agent_context.tool_instances[tool_name] = mock_tool_instance
    agent_context.get_tool = MagicMock(return_value=mock_tool_instance)


    with caplog.at_level(logging.ERROR): # Exception is logged as error
        await approved_tool_handler.handle(event, agent_context)

    expected_error_message_in_log = f"Error executing approved tool '{tool_name}' (ID: {tool_invocation_id}): {exception_message}"
    assert expected_error_message_in_log in caplog.text

    # Check tool log queue for call and exception
    expected_log_call = f"[APPROVED_TOOL_CALL] Agent_ID: {agent_context.agent_id}, Tool: {tool_name}, Invocation_ID: {tool_invocation_id}, Arguments: {json.dumps(tool_args)}"
    expected_log_exception = f"[APPROVED_TOOL_EXCEPTION] Agent_ID: {agent_context.agent_id}, Tool: {tool_name}, Invocation_ID: {tool_invocation_id}, Exception: {expected_error_message_in_log}"
    
    put_calls = [args[0][0] for args in agent_context.queues.tool_interaction_log_queue.put.call_args_list]
    assert expected_log_call in put_calls
    assert expected_log_exception in put_calls

    # Check history update
    agent_context.add_message_to_history.assert_called_once_with({
        "role": "tool",
        "tool_call_id": tool_invocation_id,
        "name": tool_name,
        "content": f"Error: Approved tool '{tool_name}' execution failed. Reason: {expected_error_message_in_log}",
    })

    # Check enqueued ToolResultEvent (with error)
    agent_context.queues.enqueue_tool_result.assert_called_once()
    enqueued_event = agent_context.queues.enqueue_tool_result.call_args[0][0]
    assert enqueued_event.error == expected_error_message_in_log
    assert enqueued_event.tool_invocation_id == tool_invocation_id

@pytest.mark.asyncio
async def test_handle_invalid_event_type(approved_tool_handler: ApprovedToolInvocationEventHandler, agent_context, caplog):
    """Test that the handler skips events that are not ApprovedToolInvocationEvent."""
    invalid_event = GenericEvent(payload={}, type_name="wrong_event")

    with caplog.at_level(logging.WARNING):
        await approved_tool_handler.handle(invalid_event, agent_context) # type: ignore
    
    assert f"ApprovedToolInvocationEventHandler received non-ApprovedToolInvocationEvent: {type(invalid_event)}. Skipping." in caplog.text
    agent_context.queues.tool_interaction_log_queue.put.assert_not_called()
    agent_context.add_message_to_history.assert_not_called()
    agent_context.queues.enqueue_tool_result.assert_not_called()


@pytest.mark.asyncio
async def test_handle_json_serialization_error_for_logs_args(approved_tool_handler: ApprovedToolInvocationEventHandler, agent_context, mock_tool_instance, caplog):
    """Test that if arguments are not JSON serializable, str() is used for logging."""
    tool_name = "mock_tool"
    # Arguments that are not directly JSON serializable (e.g., a set)
    unserializable_args = {"param1": {1, 2, 3}} # set is not JSON serializable
    tool_invocation_id = "json-err-args-id"
    
    tool_invocation = ToolInvocation(name=tool_name, arguments=unserializable_args, id=tool_invocation_id)
    event = ApprovedToolInvocationEvent(tool_invocation=tool_invocation)

    mock_tool_instance.execute = AsyncMock(return_value="result")
    agent_context.tool_instances[tool_name] = mock_tool_instance
    agent_context.get_tool = MagicMock(return_value=mock_tool_instance)

    await approved_tool_handler.handle(event, agent_context)

    expected_log_call_str_args = f"[APPROVED_TOOL_CALL] Agent_ID: {agent_context.agent_id}, Tool: {tool_name}, Invocation_ID: {tool_invocation_id}, Arguments: {str(unserializable_args)}"
    put_calls = [args[0][0] for args in agent_context.queues.tool_interaction_log_queue.put.call_args_list]
    assert expected_log_call_str_args in put_calls


@pytest.mark.asyncio
async def test_handle_json_serialization_error_for_logs_result(approved_tool_handler: ApprovedToolInvocationEventHandler, agent_context, mock_tool_instance, caplog):
    """Test that if tool result is not JSON serializable, str() is used for logging."""
    tool_name = "mock_tool"
    tool_args = {"param1": "val"}
    tool_invocation_id = "json-err-res-id"
    
    unserializable_result = {1, 2, 3} # A set
    tool_invocation = ToolInvocation(name=tool_name, arguments=tool_args, id=tool_invocation_id)
    event = ApprovedToolInvocationEvent(tool_invocation=tool_invocation)

    mock_tool_instance.execute = AsyncMock(return_value=unserializable_result)
    agent_context.tool_instances[tool_name] = mock_tool_instance
    agent_context.get_tool = MagicMock(return_value=mock_tool_instance)

    await approved_tool_handler.handle(event, agent_context)
    
    expected_log_result_str = f"[APPROVED_TOOL_RESULT] Agent_ID: {agent_context.agent_id}, Tool: {tool_name}, Invocation_ID: {tool_invocation_id}, Outcome (first 200 chars): {str(unserializable_result)[:200]}"
    put_calls = [args[0][0] for args in agent_context.queues.tool_interaction_log_queue.put.call_args_list]
    assert any(c.startswith(f"[APPROVED_TOOL_RESULT] Agent_ID: {agent_context.agent_id}, Tool: {tool_name}, Invocation_ID: {tool_invocation_id}, Outcome (first 200 chars): {str(unserializable_result)[:200]}") for c in put_calls)


def test_approved_tool_handler_initialization(caplog):
    with caplog.at_level(logging.INFO):
        handler = ApprovedToolInvocationEventHandler()
    assert "ApprovedToolInvocationEventHandler initialized." in caplog.text

