import pytest
import logging
import json
from unittest.mock import MagicMock, patch

from autobyteus.agent.handlers.tool_result_event_handler import ToolResultEventHandler
from autobyteus.agent.events.agent_events import ToolResultEvent, LLMPromptReadyEvent
from autobyteus.llm.user_message import LLMUserMessage

@pytest.fixture
def tool_result_handler():
    return ToolResultEventHandler()

@pytest.mark.asyncio
async def test_handle_tool_result_success(tool_result_handler: ToolResultEventHandler, agent_context, caplog):
    """Test successful handling of a ToolResultEvent (no error)."""
    tool_name = "calculator"
    tool_result_data = {"sum": 15}
    tool_invocation_id = "calc-123"
    event = ToolResultEvent(tool_name=tool_name, result=tool_result_data, tool_invocation_id=tool_invocation_id)

    with caplog.at_level(logging.INFO):
        await tool_result_handler.handle(event, agent_context)

    # Check logs
    assert f"Agent '{agent_context.agent_id}' handling ToolResultEvent from tool: '{tool_name}' (Invocation ID: {tool_invocation_id})" in caplog.text
    
    log_msg_success_processed = f"[TOOL_RESULT_SUCCESS_PROCESSED] Agent_ID: {agent_context.agent_id}, Tool: {tool_name}, Invocation_ID: {tool_invocation_id}, Result (first 200 chars of stringified): {str(tool_result_data)[:200]}"
    agent_context.queues.tool_interaction_log_queue.put.assert_called_once_with(log_msg_success_processed)

    # Check enqueued LLMPromptReadyEvent
    agent_context.queues.enqueue_internal_system_event.assert_called_once()
    enqueued_event = agent_context.queues.enqueue_internal_system_event.call_args[0][0]
    assert isinstance(enqueued_event, LLMPromptReadyEvent)
    assert isinstance(enqueued_event.llm_user_message, LLMUserMessage)
    
    expected_llm_content_part1 = f"The tool '{tool_name}' (invocation ID: {tool_invocation_id}) has executed."
    expected_llm_content_part2 = f"Result:\n{json.dumps(tool_result_data, indent=2)}" # Assuming JSON dump for dicts
    assert expected_llm_content_part1 in enqueued_event.llm_user_message.content
    assert expected_llm_content_part2 in enqueued_event.llm_user_message.content


@pytest.mark.asyncio
async def test_handle_tool_result_with_error(tool_result_handler: ToolResultEventHandler, agent_context, caplog):
    """Test handling of a ToolResultEvent that contains an error."""
    tool_name = "file_writer"
    error_message = "Permission denied"
    tool_invocation_id = "fw-456"
    event = ToolResultEvent(tool_name=tool_name, result=None, error=error_message, tool_invocation_id=tool_invocation_id)

    with caplog.at_level(logging.INFO):
        await tool_result_handler.handle(event, agent_context)

    assert f"Agent '{agent_context.agent_id}' handling ToolResultEvent from tool: '{tool_name}' (Invocation ID: {tool_invocation_id}). Error: True" in caplog.text
    
    log_msg_error_processed = f"[TOOL_RESULT_ERROR_PROCESSED] Agent_ID: {agent_context.agent_id}, Tool: {tool_name}, Invocation_ID: {tool_invocation_id}, Error: {error_message}"
    agent_context.queues.tool_interaction_log_queue.put.assert_called_once_with(log_msg_error_processed)

    agent_context.queues.enqueue_internal_system_event.assert_called_once()
    enqueued_event = agent_context.queues.enqueue_internal_system_event.call_args[0][0]
    assert isinstance(enqueued_event, LLMPromptReadyEvent)
    
    expected_llm_content_part1 = f"The tool '{tool_name}' (invocation ID: {tool_invocation_id}) encountered an error."
    expected_llm_content_part2 = f"Error details: {error_message}"
    assert expected_llm_content_part1 in enqueued_event.llm_user_message.content
    assert expected_llm_content_part2 in enqueued_event.llm_user_message.content


@pytest.mark.asyncio
async def test_handle_tool_result_no_invocation_id(tool_result_handler: ToolResultEventHandler, agent_context, caplog):
    """Test handling when tool_invocation_id is None."""
    tool_name = "status_checker"
    tool_result_data = "System OK"
    event = ToolResultEvent(tool_name=tool_name, result=tool_result_data, tool_invocation_id=None) # No ID

    await tool_result_handler.handle(event, agent_context)

    # Check that 'N/A' is used for invocation ID in logs and messages
    assert "(Invocation ID: N/A)" in caplog.text
    log_msg_success_processed = f"[TOOL_RESULT_SUCCESS_PROCESSED] Agent_ID: {agent_context.agent_id}, Tool: {tool_name}, Invocation_ID: N/A, Result (first 200 chars of stringified): {str(tool_result_data)[:200]}"
    agent_context.queues.tool_interaction_log_queue.put.assert_called_once_with(log_msg_success_processed)

    enqueued_event = agent_context.queues.enqueue_internal_system_event.call_args[0][0]
    assert "(invocation ID: N/A)" in enqueued_event.llm_user_message.content

@pytest.mark.asyncio
async def test_handle_tool_result_truncation(tool_result_handler: ToolResultEventHandler, agent_context):
    """Test that large tool results are truncated for the LLM prompt."""
    tool_name = "data_loader"
    long_result = "a" * 3000 # Result longer than max_len (2000)
    event = ToolResultEvent(tool_name=tool_name, result=long_result, tool_invocation_id="dl-789")

    await tool_result_handler.handle(event, agent_context)

    enqueued_event = agent_context.queues.enqueue_internal_system_event.call_args[0][0]
    llm_content = enqueued_event.llm_user_message.content
    
    assert len(llm_content) < len(long_result) + 500 # Check it's substantially shorter
    assert "... (result truncated, original length 3000)" in llm_content
    assert long_result[:1000] in llm_content # Beginning of the result should be there

@pytest.mark.asyncio
async def test_handle_tool_result_non_string_json_serializable(tool_result_handler: ToolResultEventHandler, agent_context):
    """Test handling of tool results that are dicts/lists (JSON serializable)."""
    tool_name = "config_reader"
    dict_result = {"key": "value", "nested": {"num": 1}}
    event = ToolResultEvent(tool_name=tool_name, result=dict_result, tool_invocation_id="cr-001")

    await tool_result_handler.handle(event, agent_context)
    enqueued_event = agent_context.queues.enqueue_internal_system_event.call_args[0][0]
    llm_content = enqueued_event.llm_user_message.content
    
    expected_json_str = json.dumps(dict_result, indent=2)
    assert f"Result:\n{expected_json_str}" in llm_content

@pytest.mark.asyncio
async def test_handle_tool_result_non_json_serializable_object(tool_result_handler: ToolResultEventHandler, agent_context):
    """Test handling of tool results that are objects not directly JSON serializable."""
    class MyObject:
        def __init__(self, val): self.val = val
        def __str__(self): return f"MyObject(val={self.val})"
    
    obj_result = MyObject("test_data")
    event = ToolResultEvent(tool_name="object_tool", result=obj_result, tool_invocation_id="obj-002")

    await tool_result_handler.handle(event, agent_context)
    enqueued_event = agent_context.queues.enqueue_internal_system_event.call_args[0][0]
    llm_content = enqueued_event.llm_user_message.content
    
    assert f"Result:\n{str(obj_result)}" in llm_content


@pytest.mark.asyncio
async def test_handle_invalid_event_type(tool_result_handler: ToolResultEventHandler, agent_context, caplog):
    """Test that the handler skips events that are not ToolResultEvent."""
    from autobyteus.agent.events.agent_events import GenericEvent # Example of a different event
    invalid_event = GenericEvent(payload={}, type_name="wrong_event")

    with caplog.at_level(logging.WARNING):
        await tool_result_handler.handle(invalid_event, agent_context) # type: ignore
    
    assert f"ToolResultEventHandler received non-ToolResultEvent: {type(invalid_event)}. Skipping." in caplog.text
    agent_context.queues.tool_interaction_log_queue.put.assert_not_called()
    agent_context.queues.enqueue_internal_system_event.assert_not_called()


def test_tool_result_handler_initialization(caplog):
    with caplog.at_level(logging.INFO):
        handler = ToolResultEventHandler()
    assert "ToolResultEventHandler initialized." in caplog.text

