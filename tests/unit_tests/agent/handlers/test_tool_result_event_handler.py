import pytest
import logging
import json
from unittest.mock import AsyncMock, MagicMock

from autobyteus.agent.handlers.tool_result_event_handler import ToolResultEventHandler
from autobyteus.agent.events.agent_events import ToolResultEvent, UserMessageReceivedEvent, GenericEvent
from autobyteus.agent.tool_invocation import ToolInvocation, ToolInvocationTurn
from autobyteus.agent.sender_type import SenderType
from autobyteus.agent.message.context_file import ContextFile

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

    # Assert that the correct event was enqueued for the input pipeline
    agent_context.input_event_queues.enqueue_user_message.assert_called_once()
    enqueued_event = agent_context.input_event_queues.enqueue_user_message.call_args[0][0]
    assert isinstance(enqueued_event, UserMessageReceivedEvent)
    
    # Assert the content of the message sent to the pipeline
    agent_input_message = enqueued_event.agent_input_user_message
    assert agent_input_message.sender_type == SenderType.TOOL
    assert f"Tool: {tool_name} (ID: {tool_invocation_id})" in agent_input_message.content
    assert "Status: Success" in agent_input_message.content
    assert f"Result:\n{json.dumps(tool_result_data, indent=2)}" in agent_input_message.content
    assert not agent_input_message.context_files

@pytest.mark.asyncio
async def test_handle_single_tool_result_with_error(tool_result_handler: ToolResultEventHandler, agent_context, mock_notifier, caplog):
    """Test handling of a single errored ToolResultEvent."""
    tool_name = "write_file"
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

    # Assert message sent to pipeline
    agent_context.input_event_queues.enqueue_user_message.assert_called_once()
    enqueued_event = agent_context.input_event_queues.enqueue_user_message.call_args[0][0]
    agent_input_message = enqueued_event.agent_input_user_message
    assert agent_input_message.sender_type == SenderType.TOOL
    assert f"Tool: {tool_name} (ID: {tool_invocation_id})" in agent_input_message.content
    assert "Status: Error" in agent_input_message.content
    assert f"Details: {error_message}" in agent_input_message.content

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
    agent_context.input_event_queues.enqueue_user_message.assert_not_called() # Pipeline not triggered yet

    # 3. Handle second result (A)
    await tool_result_handler.handle(res_A, agent_context)
    
    # Assertions after second result
    assert "All tool results for the turn collected. Re-ordering" in caplog.text
    agent_context.input_event_queues.enqueue_user_message.assert_called_once()
    enqueued_event = agent_context.input_event_queues.enqueue_user_message.call_args[0][0]
    agent_input_message = enqueued_event.agent_input_user_message
    content = agent_input_message.content

    # CRITICAL: Assert that the final output is in the correct A -> B order
    pos_A = content.find("Tool: tool_A (ID: call_A)")
    pos_B = content.find("Tool: tool_B (ID: call_B)")
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

    # Assert final message order is correct (A then B)
    agent_context.input_event_queues.enqueue_user_message.assert_called_once()
    enqueued_event = agent_context.input_event_queues.enqueue_user_message.call_args[0][0]
    content = enqueued_event.agent_input_user_message.content

    pos_A_success = content.find("Tool: tool_A (ID: call_A)")
    pos_B_error = content.find("Tool: tool_B (ID: call_B)")
    assert pos_A_success != -1 and pos_B_error != -1
    assert pos_A_success < pos_B_error
    assert "Status: Success" in content[pos_A_success:pos_B_error]
    assert "Status: Error" in content[pos_B_error:]
    assert "Details: Failed B" in content[pos_B_error:]

# === New Tests for Media/ContextFile Handling ===

@pytest.mark.asyncio
async def test_handle_single_tool_result_with_context_file(tool_result_handler: ToolResultEventHandler, agent_context):
    """Test that a tool result containing a ContextFile is handled correctly."""
    context_file = ContextFile(uri="/path/to/image.png", file_name="image.png")
    event = ToolResultEvent(tool_name="read_media_file", result=context_file, tool_invocation_id="media-1")
    
    await tool_result_handler.handle(event, agent_context)

    agent_context.input_event_queues.enqueue_user_message.assert_called_once()
    enqueued_event = agent_context.input_event_queues.enqueue_user_message.call_args[0][0]
    
    assert isinstance(enqueued_event, UserMessageReceivedEvent)
    
    agent_input_message = enqueued_event.agent_input_user_message
    assert agent_input_message.sender_type == SenderType.TOOL
    assert "The file 'image.png' has been loaded into the context" in agent_input_message.content
    assert agent_input_message.context_files == [context_file]

@pytest.mark.asyncio
async def test_handle_single_tool_result_with_list_of_context_files(tool_result_handler: ToolResultEventHandler, agent_context):
    """Test that a tool result containing a list of ContextFile objects is handled correctly."""
    context_file1 = ContextFile(uri="/path/to/file1.txt", file_name="file1.txt")
    context_file2 = ContextFile(uri="/path/to/file2.log", file_name="file2.log")
    context_files_list = [context_file1, context_file2]
    
    event = ToolResultEvent(tool_name="ListFiles", result=context_files_list, tool_invocation_id="list-1")
    
    await tool_result_handler.handle(event, agent_context)

    agent_context.input_event_queues.enqueue_user_message.assert_called_once()
    enqueued_event = agent_context.input_event_queues.enqueue_user_message.call_args[0][0]
    
    assert isinstance(enqueued_event, UserMessageReceivedEvent)
    
    agent_input_message = enqueued_event.agent_input_user_message
    assert agent_input_message.sender_type == SenderType.TOOL
    
    # Check that the text content mentions the list of files
    assert "The following files have been loaded into the context" in agent_input_message.content
    assert "['file1.txt', 'file2.log']" in agent_input_message.content
    
    # Check that the context_files list is correctly populated
    assert agent_input_message.context_files == context_files_list

@pytest.mark.asyncio
async def test_handle_multi_tool_with_mixed_media_and_text(tool_result_handler: ToolResultEventHandler, agent_context):
    """Test a multi-tool turn with both media and text results are aggregated correctly."""
    context_file = ContextFile(uri="/path/to/image.png", file_name="image.png")
    
    inv_A = ToolInvocation("read_media_file", {"path": "/path/to/image.png"}, id="media-1")
    inv_B = ToolInvocation("calculator", {"op": "add"}, id="calc-1")
    agent_context.state.active_multi_tool_call_turn = ToolInvocationTurn(invocations=[inv_A, inv_B])

    res_A = ToolResultEvent(tool_name="read_media_file", result=context_file, tool_invocation_id="media-1")
    res_B = ToolResultEvent(tool_name="calculator", result={"sum": 5}, tool_invocation_id="calc-1")

    # Handle both results
    await tool_result_handler.handle(res_A, agent_context)
    await tool_result_handler.handle(res_B, agent_context)

    # Assertions
    agent_context.input_event_queues.enqueue_user_message.assert_called_once()
    enqueued_event = agent_context.input_event_queues.enqueue_user_message.call_args[0][0]
    
    agent_input_message = enqueued_event.agent_input_user_message
    assert agent_input_message.sender_type == SenderType.TOOL
    assert agent_input_message.context_files == [context_file]

    # Check that text content for both results is present and in order
    content = agent_input_message.content
    pos_A = content.find("Tool: read_media_file")
    pos_B = content.find("Tool: calculator")
    assert pos_A < pos_B
    assert "The file 'image.png' has been loaded" in content
    assert '"sum": 5' in content

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
    enqueued_event = agent_context.input_event_queues.enqueue_user_message.call_args[0][0]
    content = enqueued_event.agent_input_user_message.content
    
    assert f"Result:\n{str(obj_result)}" in content

@pytest.mark.asyncio
async def test_handle_invalid_event_type(tool_result_handler: ToolResultEventHandler, agent_context, mock_notifier, caplog):
    """Test that the handler skips events that are not ToolResultEvent."""
    invalid_event = GenericEvent(payload={}, type_name="wrong_event")

    with caplog.at_level(logging.WARNING):
        await tool_result_handler.handle(invalid_event, agent_context)
    
    assert f"ToolResultEventHandler received non-ToolResultEvent: {type(invalid_event)}. Skipping." in caplog.text
    mock_notifier.notify_agent_data_tool_log.assert_not_called()
    agent_context.input_event_queues.enqueue_user_message.assert_not_called()

def test_tool_result_handler_initialization(caplog):
    """Test simple initialization of the handler."""
    with caplog.at_level(logging.INFO):
        handler = ToolResultEventHandler()
    assert "ToolResultEventHandler initialized." in caplog.text
