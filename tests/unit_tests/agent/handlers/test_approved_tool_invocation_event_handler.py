# file: autobyteus/tests/unit_tests/agent/handlers/test_approved_tool_invocation_event_handler.py
import pytest
import logging
import json
import traceback
from unittest.mock import MagicMock, AsyncMock, patch, ANY

from autobyteus.agent.handlers.approved_tool_invocation_event_handler import ApprovedToolInvocationEventHandler
from autobyteus.agent.events.agent_events import ApprovedToolInvocationEvent, ToolResultEvent, GenericEvent
from autobyteus.agent.tool_invocation import ToolInvocation
from autobyteus.tools.base_tool import BaseTool


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

    mock_tool_instance.execute = AsyncMock(return_value="Successful execution result")
    # The agent_context from conftest already provides a get_tool that returns the mock_tool_instance
    
    with caplog.at_level(logging.INFO):
        await approved_tool_handler.handle(event, agent_context)

    assert f"Agent '{agent_context.agent_id}' handling ApprovedToolInvocationEvent for tool: '{tool_name}' (ID: {tool_invocation_id})" in caplog.text
    assert f"Approved tool '{tool_name}' (ID: {tool_invocation_id}) executed successfully by agent '{agent_context.agent_id}'" in caplog.text

    expected_log_call_str = f"[APPROVED_TOOL_CALL] Agent_ID: {agent_context.agent_id}, Tool: {tool_name}, Invocation_ID: {tool_invocation_id}, Arguments: {json.dumps(tool_args)}"
    expected_log_result_str = f"[APPROVED_TOOL_RESULT] Agent_ID: {agent_context.agent_id}, Tool: {tool_name}, Invocation_ID: {tool_invocation_id}, Outcome (first 200 chars): \"Successful execution result\""
    
    # Check calls to notifier (which is on the status_manager in the fixture)
    agent_context.status_manager.notifier.notify_agent_data_tool_log.assert_any_call({
        "log_entry": ANY,
        "tool_invocation_id": tool_invocation_id,
        "tool_name": tool_name
    })
    agent_context.status_manager.notifier.notify_agent_data_tool_log.assert_any_call({
        "log_entry": ANY,
        "tool_invocation_id": tool_invocation_id,
        "tool_name": tool_name
    })


    agent_context.state.add_message_to_history.assert_called_once_with({ 
        "role": "tool",
        "tool_call_id": tool_invocation_id,
        "name": tool_name,
        "content": "Successful execution result",
    })

    agent_context.input_event_queues.enqueue_tool_result.assert_called_once()
    enqueued_event = agent_context.input_event_queues.enqueue_tool_result.call_args[0][0]
    assert isinstance(enqueued_event, ToolResultEvent)
    assert enqueued_event.tool_name == tool_name
    assert enqueued_event.result == "Successful execution result"
    assert enqueued_event.error is None
    assert enqueued_event.tool_invocation_id == tool_invocation_id

    mock_tool_instance.execute.assert_called_once_with(context=agent_context, **tool_args)


@pytest.mark.asyncio
async def test_handle_approved_tool_not_found(approved_tool_handler: ApprovedToolInvocationEventHandler, agent_context, caplog):
    """Test handling when the specified tool is not found in the agent's context."""
    tool_name = "non_existent_tool"
    tool_args = {"param": "val"}
    tool_invocation_id = "notfound-tool-id-456"
    
    tool_invocation = ToolInvocation(name=tool_name, arguments=tool_args, id=tool_invocation_id)
    event = ApprovedToolInvocationEvent(tool_invocation=tool_invocation)

    agent_context.get_tool = MagicMock(return_value=None)
    
    with caplog.at_level(logging.ERROR):
        await approved_tool_handler.handle(event, agent_context)

    error_message = f"Tool '{tool_name}' not found or configured for agent '{agent_context.agent_id}'."
    assert error_message in caplog.text

    expected_log_call_str = f"[APPROVED_TOOL_CALL] Agent_ID: {agent_context.agent_id}, Tool: {tool_name}, Invocation_ID: {tool_invocation_id}, Arguments: {json.dumps(tool_args)}"
    expected_log_error_str = f"[APPROVED_TOOL_ERROR] Agent_ID: {agent_context.agent_id}, Tool: {tool_name}, Invocation_ID: {tool_invocation_id}, Error: {error_message}"
    
    agent_context.status_manager.notifier.notify_agent_data_tool_log.assert_any_call({
        "log_entry": ANY,
        "tool_invocation_id": tool_invocation_id,
        "tool_name": tool_name
    })
    agent_context.status_manager.notifier.notify_agent_data_tool_log.assert_any_call({
        "log_entry": ANY,
        "tool_invocation_id": tool_invocation_id,
        "tool_name": tool_name
    })
    agent_context.status_manager.notifier.notify_agent_error_output_generation.assert_called_once_with(
        error_source=f"ApprovedToolExecution.ToolNotFound.{tool_name}",
        error_message=error_message
    )

    agent_context.state.add_message_to_history.assert_called_once_with({ 
        "role": "tool",
        "tool_call_id": tool_invocation_id,
        "name": tool_name,
        "content": f"Error: Approved tool '{tool_name}' execution failed. Reason: {error_message}",
    })

    agent_context.input_event_queues.enqueue_tool_result.assert_called_once()
    enqueued_event = agent_context.input_event_queues.enqueue_tool_result.call_args[0][0]
    assert isinstance(enqueued_event, ToolResultEvent)
    assert enqueued_event.tool_name == tool_name
    assert enqueued_event.result is None
    assert enqueued_event.error == error_message
    assert enqueued_event.tool_invocation_id == tool_invocation_id


@pytest.mark.asyncio
async def test_handle_approved_tool_execution_exception(approved_tool_handler: ApprovedToolInvocationEventHandler, agent_context, caplog):
    """Test handling when tool execution raises an exception."""
    tool_name = "failing_tool" 
    tool_args = {}
    tool_invocation_id = "fail-tool-id-789"
    
    tool_invocation = ToolInvocation(name=tool_name, arguments=tool_args, id=tool_invocation_id)
    event = ApprovedToolInvocationEvent(tool_invocation=tool_invocation)

    exception_message = "Simulated tool execution failure!"
    
    failing_mock_tool = MagicMock(spec=BaseTool) 
    failing_mock_tool.execute = AsyncMock(side_effect=Exception(exception_message))
    failing_mock_tool.get_name = MagicMock(return_value=tool_name) 
    
    agent_context.get_tool = MagicMock(return_value=failing_mock_tool)
    
    with caplog.at_level(logging.ERROR):
        await approved_tool_handler.handle(event, agent_context)

    expected_error_message_in_log = f"Error executing approved tool '{tool_name}' (ID: {tool_invocation_id}): {exception_message}"
    assert expected_error_message_in_log in caplog.text

    expected_log_call_str = f"[APPROVED_TOOL_CALL] Agent_ID: {agent_context.agent_id}, Tool: {tool_name}, Invocation_ID: {tool_invocation_id}, Arguments: {json.dumps(tool_args)}"
    expected_log_exception_str = f"[APPROVED_TOOL_EXCEPTION] Agent_ID: {agent_context.agent_id}, Tool: {tool_name}, Invocation_ID: {tool_invocation_id}, Exception: {expected_error_message_in_log}"
    
    agent_context.status_manager.notifier.notify_agent_data_tool_log.assert_any_call({
        "log_entry": ANY,
        "tool_invocation_id": tool_invocation_id,
        "tool_name": tool_name
    })
    agent_context.status_manager.notifier.notify_agent_data_tool_log.assert_any_call({
        "log_entry": ANY,
        "tool_invocation_id": tool_invocation_id,
        "tool_name": tool_name
    })
    
    agent_context.status_manager.notifier.notify_agent_error_output_generation.assert_called_once()
    call_args_error_gen = agent_context.status_manager.notifier.notify_agent_error_output_generation.call_args[1] # kwargs
    assert call_args_error_gen['error_source'] == f"ApprovedToolExecution.Exception.{tool_name}"
    assert call_args_error_gen['error_message'] == expected_error_message_in_log
    assert isinstance(call_args_error_gen['error_details'], str)

    agent_context.state.add_message_to_history.assert_called_once_with({ 
        "role": "tool",
        "tool_call_id": tool_invocation_id,
        "name": tool_name,
        "content": f"Error: Approved tool '{tool_name}' execution failed. Reason: {expected_error_message_in_log}",
    })

    agent_context.input_event_queues.enqueue_tool_result.assert_called_once()
    enqueued_event = agent_context.input_event_queues.enqueue_tool_result.call_args[0][0]
    assert enqueued_event.error == expected_error_message_in_log
    assert enqueued_event.tool_invocation_id == tool_invocation_id

@pytest.mark.asyncio
async def test_handle_invalid_event_type(approved_tool_handler: ApprovedToolInvocationEventHandler, agent_context, caplog):
    """Test that the handler skips events that are not ApprovedToolInvocationEvent."""
    invalid_event = GenericEvent(payload={}, type_name="wrong_event")
    
    with caplog.at_level(logging.WARNING):
        await approved_tool_handler.handle(invalid_event, agent_context)
    
    assert f"ApprovedToolInvocationEventHandler received non-ApprovedToolInvocationEvent: {type(invalid_event)}. Skipping." in caplog.text
    agent_context.status_manager.notifier.notify_agent_data_tool_log.assert_not_called()
    agent_context.state.add_message_to_history.assert_not_called()
    agent_context.input_event_queues.enqueue_tool_result.assert_not_called()

@pytest.mark.asyncio
async def test_handle_json_serialization_error_for_logs_args(approved_tool_handler: ApprovedToolInvocationEventHandler, agent_context, mock_tool_instance):
    """Test that if arguments are not JSON serializable, str() is used for logging."""
    tool_name = "mock_tool"
    unserializable_args = {"param1": {1, 2, 3}} 
    tool_invocation_id = "json-err-args-id"
    
    tool_invocation = ToolInvocation(name=tool_name, arguments=unserializable_args, id=tool_invocation_id)
    event = ApprovedToolInvocationEvent(tool_invocation=tool_invocation)

    mock_tool_instance.execute = AsyncMock(return_value="result")
    
    await approved_tool_handler.handle(event, agent_context)

    expected_log_call_str_args = f"[APPROVED_TOOL_CALL] Agent_ID: {agent_context.agent_id}, Tool: {tool_name}, Invocation_ID: {tool_invocation_id}, Arguments: {str(unserializable_args)}"
    agent_context.status_manager.notifier.notify_agent_data_tool_log.assert_any_call({
        "log_entry": ANY,
        "tool_invocation_id": tool_invocation_id,
        "tool_name": tool_name
    })

@pytest.mark.asyncio
async def test_handle_json_serialization_error_for_logs_result(approved_tool_handler: ApprovedToolInvocationEventHandler, agent_context, mock_tool_instance):
    """Test that if tool result is not JSON serializable, str() is used for logging."""
    tool_name = "mock_tool"
    tool_args = {"param1": "val"}
    tool_invocation_id = "json-err-res-id"
    
    unserializable_result = {1, 2, 3} 
    tool_invocation = ToolInvocation(name=tool_name, arguments=tool_args, id=tool_invocation_id)
    event = ApprovedToolInvocationEvent(tool_invocation=tool_invocation)

    mock_tool_instance.execute = AsyncMock(return_value=unserializable_result)
    
    await approved_tool_handler.handle(event, agent_context)
    
    expected_log_result_str = f"[APPROVED_TOOL_RESULT] Agent_ID: {agent_context.agent_id}, Tool: {tool_name}, Invocation_ID: {tool_invocation_id}, Outcome (first 200 chars): {str(unserializable_result)[:200]}"
    agent_context.status_manager.notifier.notify_agent_data_tool_log.assert_any_call({
        "log_entry": ANY,
        "tool_invocation_id": tool_invocation_id,
        "tool_name": tool_name
    })

def test_approved_tool_handler_initialization(caplog):
    with caplog.at_level(logging.INFO):
        handler = ApprovedToolInvocationEventHandler()
    assert "ApprovedToolInvocationEventHandler initialized." in caplog.text
