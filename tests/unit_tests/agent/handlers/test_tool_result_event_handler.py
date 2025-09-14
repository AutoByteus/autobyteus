import pytest
import logging
import json
from unittest.mock import AsyncMock, MagicMock

from autobyteus.agent.handlers.tool_result_event_handler import ToolResultEventHandler
from autobyteus.agent.events.agent_events import ToolResultEvent, LLMUserMessageReadyEvent, GenericEvent, PendingToolInvocationEvent
from autobyteus.llm.user_message import LLMUserMessage
from autobyteus.agent.tool_invocation import ToolInvocation, ToolInvocationTurn

@pytest.fixture
def tool_result_handler():
    """Fixture for a ToolResultEventHandler instance."""
    return ToolResultEventHandler()

@pytest.fixture
def mock_notifier(agent_context):
    """Fixture to ensure the notifier is a mock."""
    notifier = AsyncMock()
    agent_context.phase_manager.notifier = notifier
    return notifier

# === Single Tool Call Tests ===

@pytest.mark.asyncio
async def test_handle_single_tool_result_success(tool_result_handler: ToolResultEventHandler, agent_context, mock_notifier, caplog):
    """Test successful handling of a single ToolResultEvent when no multi-tool turn is active."""
    tool_name = "calculator"
    tool_result_data = {"sum": 15}
    tool_invocation_id = "calc-123"
    event = ToolResultEvent(tool_name=tool_name, result=tool_result_data, tool_invocation_id=tool_invocation_id)

    # Pre-condition: no active turn
    agent_context.state.active_multi_tool_call_turn = None

    with caplog.at_level(logging.INFO):
        await tool_result_handler.handle(event, agent_context)

    assert f"Agent '{agent_context.agent_id}' handling single ToolResultEvent from tool: '{tool_name}'." in caplog.text
    
    # Assert notifier was called with the correct dictionary payload
    expected_log_msg = f"[TOOL_RESULT_SUCCESS_PROCESSED] Agent_ID: {agent_context.agent_id}, Tool: {tool_name}, Invocation_ID: {tool_invocation_id}, Result: {str(tool_result_data)}"
    mock_notifier.notify_agent_data_tool_log.assert_called_once_with({
        "log_entry": expected_log_msg,
        "tool_invocation_id": tool_invocation_id,
        "tool_name": tool_name,
    })

    # Assert that the correct event was enqueued for the LLM
    agent_context.input_event_queues.enqueue_internal_system_event.assert_called_once()
    enqueued_event = agent_context.input_event_queues.enqueue_internal_system_event.call_args[0][0]
    assert isinstance(enqueued_event, LLMUserMessageReadyEvent)
    
    # Assert the content of the message sent to the LLM
    llm_content = enqueued_event.llm_user_message.content
    assert f"Tool: {tool_name} (ID: {tool_invocation_id})" in llm_content
    assert "Status: Success" in llm_content
    assert f"Result:\n{json.dumps(tool_result_data, indent=2)}" in llm_content

@pytest.mark.asyncio
async def test_handle_single_tool_result_with_error(tool_result_handler: ToolResultEventHandler, agent_context, mock_notifier, caplog):
    """Test handling of a single errored ToolResultEvent."""
    tool_name = "file_writer"
    error_message = "Permission denied"
    tool_invocation_id = "fw-456"
    event = ToolResultEvent(tool_name=tool_name, result=None, error=error_message, tool_invocation_id=tool_invocation_id)

    agent_context.state.active_multi_tool_call_turn = None

    await tool_result_handler.handle(event, agent_context)

    # Assert notifier call
    expected_log_msg = f"[TOOL_RESULT_ERROR_PROCESSED] Agent_ID: {agent_context.agent_id}, Tool: {tool_name}, Invocation_ID: {tool_invocation_id}, Error: {error_message}"
    mock_notifier.notify_agent_data_tool_log.assert_called_once_with({
        "log_entry": expected_log_msg,
        "tool_invocation_id": tool_invocation_id,
        "tool_name": tool_name,
    })

    # Assert LLM message
    agent_context.input_event_queues.enqueue_internal_system_event.assert_called_once()
    enqueued_event = agent_context.input_event_queues.enqueue_internal_system_event.call_args[0][0]
    llm_content = enqueued_event.llm_user_message.content
    assert f"Tool: {tool_name} (ID: {tool_invocation_id})" in llm_content
    assert "Status: Error" in llm_content
    assert f"Details: {error_message}" in llm_content

# === Multi-Tool Call Tests ===

@pytest.mark.asyncio
async def test_handle_multi_tool_results_reorders_correctly(tool_result_handler: ToolResultEventHandler, agent_context, mock_notifier, caplog):
    """Test that results arriving out of order are correctly re-ordered before sending to the LLM."""
    # 1. Setup
    inv_A = ToolInvocation("tool_A", {"arg": "A"}, id="call_A")
    inv_B = ToolInvocation("tool_B", {"arg": "B"}, id="call_B")
    
    # The required final order
    agent_context.state.active_multi_tool_call_turn = ToolInvocationTurn(invocations=[inv_A, inv_B])

    res_B = ToolResultEvent(tool_name="tool_B", result="Result B", tool_invocation_id="call_B")
    res_A = ToolResultEvent(tool_name="tool_A", result="Result A", tool_invocation_id="call_A")

    # 2. Handle first result (B, arrives out of order)
    with caplog.at_level(logging.INFO):
        await tool_result_handler.handle(res_B, agent_context)

    # Assertions after first result
    assert "Collected 1/2 results." in caplog.text
    assert len(agent_context.state.active_multi_tool_call_turn.results) == 1
    mock_notifier.notify_agent_data_tool_log.assert_called_once() # Notifier is called immediately
    agent_context.input_event_queues.enqueue_internal_system_event.assert_not_called() # LLM not called yet

    # 3. Handle second result (A)
    await tool_result_handler.handle(res_A, agent_context)
    
    # Assertions after second result
    assert "All tool results for the turn collected. Re-ordering" in caplog.text
    agent_context.input_event_queues.enqueue_internal_system_event.assert_called_once()
    enqueued_event = agent_context.input_event_queues.enqueue_internal_system_event.call_args[0][0]
    llm_content = enqueued_event.llm_user_message.content

    # CRITICAL: Assert that the final output is in the correct A -> B order
    pos_A = llm_content.find("Tool: tool_A (ID: call_A)")
    pos_B = llm_content.find("Tool: tool_B (ID: call_B)")
    assert pos_A != -1 and pos_B != -1
    assert pos_A < pos_B

    # Assert state is cleaned up
    assert agent_context.state.active_multi_tool_call_turn is None

@pytest.mark.asyncio
async def test_handle_multi_tool_with_error_in_sequence(tool_result_handler: ToolResultEventHandler, agent_context, mock_notifier):
    """Test that a mix of success and error results are correctly ordered."""
    inv_A = ToolInvocation("tool_A", {"arg": "A"}, id="call_A")
    inv_B = ToolInvocation("tool_B", {"arg": "B"}, id="call_B")
    agent_context.state.active_multi_tool_call_turn = ToolInvocationTurn(invocations=[inv_A, inv_B])

    res_B_error = ToolResultEvent(tool_name="tool_B", result=None, error="Failed B", tool_invocation_id="call_B")
    res_A_success = ToolResultEvent(tool_name="tool_A", result="Success A", tool_invocation_id="call_A")

    # Handle in completion order (B then A)
    await tool_result_handler.handle(res_B_error, agent_context)
    await tool_result_handler.handle(res_A_success, agent_context)

    # Assert final LLM message order is correct (A then B)
    agent_context.input_event_queues.enqueue_internal_system_event.assert_called_once()
    enqueued_event = agent_context.input_event_queues.enqueue_internal_system_event.call_args[0][0]
    llm_content = enqueued_event.llm_user_message.content

    pos_A_success = llm_content.find("Tool: tool_A (ID: call_A)")
    pos_B_error = llm_content.find("Tool: tool_B (ID: call_B)")
    assert pos_A_success != -1 and pos_B_error != -1
    assert pos_A_success < pos_B_error
    assert "Status: Success" in llm_content[pos_A_success:pos_B_error]
    assert "Status: Error" in llm_content[pos_B_error:]
    assert "Details: Failed B" in llm_content[pos_B_error:]

# === Edge Case and Other Tests ===

@pytest.mark.asyncio
async def test_handle_tool_result_non_json_serializable_object(tool_result_handler: ToolResultEventHandler, agent_context, mock_notifier):
    """Test handling of tool results that are objects not directly JSON serializable."""
    class MyObject:
        def __init__(self, val): self.val = val
        def __str__(self): return f"MyObject(val={self.val})"
    
    obj_result = MyObject("test_data")
    event = ToolResultEvent(tool_name="object_tool", result=obj_result, tool_invocation_id="obj-002")

    await tool_result_handler.handle(event, agent_context)
    enqueued_event = agent_context.input_event_queues.enqueue_internal_system_event.call_args[0][0]
    llm_content = enqueued_event.llm_user_message.content
    
    assert f"Result:\n{str(obj_result)}" in llm_content

@pytest.mark.asyncio
async def test_handle_invalid_event_type(tool_result_handler: ToolResultEventHandler, agent_context, mock_notifier, caplog):
    """Test that the handler skips events that are not ToolResultEvent."""
    invalid_event = GenericEvent(payload={}, type_name="wrong_event")

    with caplog.at_level(logging.WARNING):
        await tool_result_handler.handle(invalid_event, agent_context)
    
    assert f"ToolResultEventHandler received non-ToolResultEvent: {type(invalid_event)}. Skipping." in caplog.text
    mock_notifier.notify_agent_data_tool_log.assert_not_called()
    agent_context.input_event_queues.enqueue_internal_system_event.assert_not_called()

def test_tool_result_handler_initialization(caplog):
    """Test simple initialization of the handler."""
    with caplog.at_level(logging.INFO):
        handler = ToolResultEventHandler()
    assert "ToolResultEventHandler initialized." in caplog.text
