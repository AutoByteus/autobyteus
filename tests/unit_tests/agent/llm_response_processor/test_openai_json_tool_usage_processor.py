# file: autobyteus/tests/unit_tests/agent/llm_response_processor/test_openai_json_tool_usage_processor.py
import pytest
import json
from unittest.mock import MagicMock, AsyncMock

from autobyteus.agent.llm_response_processor import OpenAiJsonToolUsageProcessor
from autobyteus.agent.context import AgentContext
from autobyteus.agent.events import LLMCompleteResponseReceivedEvent, PendingToolInvocationEvent
from autobyteus.llm.utils.response_types import CompleteResponse

@pytest.fixture
def processor() -> OpenAiJsonToolUsageProcessor:
    return OpenAiJsonToolUsageProcessor()

@pytest.fixture
def mock_context() -> MagicMock:
    context = MagicMock(spec=AgentContext)
    context.agent_id = "openai_test_agent"
    context.input_event_queues = AsyncMock()
    context.input_event_queues.enqueue_tool_invocation_request = AsyncMock()
    return context

@pytest.mark.asyncio
async def test_process_single_valid_tool_call_clean_json(processor, mock_context):
    """Tests a clean JSON string in the content."""
    # Arrange
    tool_call_payload = {
        "tool_calls": [
            {
                "id": "call_abc123",
                "type": "function",
                "function": {
                    "name": "get_weather",
                    "arguments": '{"location": "Boston, MA"}'
                }
            }
        ]
    }
    # The JSON string is now the content of the response
    response = CompleteResponse(content=json.dumps(tool_call_payload))
    event = LLMCompleteResponseReceivedEvent(complete_response=response)

    # Act
    result = await processor.process_response(response, mock_context, event)

    # Assert
    assert result is True
    mock_context.input_event_queues.enqueue_tool_invocation_request.assert_awaited_once()
    enqueued_event: PendingToolInvocationEvent = mock_context.input_event_queues.enqueue_tool_invocation_request.call_args[0][0]
    assert enqueued_event.tool_invocation.id == "call_abc123"
    assert enqueued_event.tool_invocation.name == "get_weather"
    assert enqueued_event.tool_invocation.arguments == {"location": "Boston, MA"}

@pytest.mark.asyncio
async def test_process_single_valid_tool_call_in_noisy_text(processor, mock_context):
    """Tests JSON embedded in conversational text."""
    # Arrange
    tool_call_payload = {
        "tool_calls": [
            {
                "id": "call_abc123",
                "type": "function",
                "function": {
                    "name": "get_weather",
                    "arguments": '{"location": "Boston, MA"}'
                }
            }
        ]
    }
    # The JSON string is now embedded in the content
    response_content = f"Of course, I can get the weather for you. Here is the tool call:\n{json.dumps(tool_call_payload)}"
    response = CompleteResponse(content=response_content)
    event = LLMCompleteResponseReceivedEvent(complete_response=response)

    # Act
    result = await processor.process_response(response, mock_context, event)

    # Assert
    assert result is True
    mock_context.input_event_queues.enqueue_tool_invocation_request.assert_awaited_once()
    enqueued_event: PendingToolInvocationEvent = mock_context.input_event_queues.enqueue_tool_invocation_request.call_args[0][0]
    assert enqueued_event.tool_invocation.name == "get_weather"

@pytest.mark.asyncio
async def test_process_multiple_valid_tool_calls(processor, mock_context):
    # Arrange
    tool_call_payload = {
        "tool_calls": [
            {
                "id": "call_abc123",
                "type": "function",
                "function": {"name": "get_weather", "arguments": '{"location": "Boston, MA"}'}
            },
            {
                "id": "call_def456",
                "type": "function",
                "function": {"name": "send_email", "arguments": '{"to": "test@example.com", "subject": "Hello"}'}
            }
        ]
    }
    # Embed the JSON payload in some conversational text
    response_content = f"Sure, I will perform those two actions for you now. {json.dumps(tool_call_payload)}"
    response = CompleteResponse(content=response_content)
    event = LLMCompleteResponseReceivedEvent(complete_response=response)

    # Act
    result = await processor.process_response(response, mock_context, event)

    # Assert
    assert result is True
    assert mock_context.input_event_queues.enqueue_tool_invocation_request.await_count == 2
    
    # Check first call
    first_call_event: PendingToolInvocationEvent = mock_context.input_event_queues.enqueue_tool_invocation_request.await_args_list[0][0][0]
    assert first_call_event.tool_invocation.id == "call_abc123"
    assert first_call_event.tool_invocation.name == "get_weather"
    
    # Check second call
    second_call_event: PendingToolInvocationEvent = mock_context.input_event_queues.enqueue_tool_invocation_request.await_args_list[1][0][0]
    assert second_call_event.tool_invocation.id == "call_def456"
    assert second_call_event.tool_invocation.name == "send_email"
    assert second_call_event.tool_invocation.arguments == {"to": "test@example.com", "subject": "Hello"}

@pytest.mark.asyncio
@pytest.mark.parametrize("bad_content", [
    "This is just a text response.", # Not JSON
    json.dumps({"tool_calls": None}), # tool_calls is not a list
    json.dumps({"tool_calls": [{"id": "call_1"}]}), # malformed call
    "This is text with an invalid json { 'key': 'val' }", # Invalid embedded JSON
])
async def test_no_or_invalid_tool_calls_in_response(processor, mock_context, bad_content):
    # Arrange
    response = CompleteResponse(content=bad_content)
    event = LLMCompleteResponseReceivedEvent(complete_response=response)
    
    # Act
    result = await processor.process_response(response, mock_context, event)
    
    # Assert
    assert result is False
    mock_context.input_event_queues.enqueue_tool_invocation_request.assert_not_awaited()

@pytest.mark.asyncio
@pytest.mark.parametrize("bad_call", [
    {"id": "call_1"}, # Missing function
    {"id": "call_1", "function": {"name": "tool"}}, # Missing arguments
    {"id": "call_1", "function": {"arguments": "{}"}}, # Missing name
    {"id": "call_1", "function": {"name": "tool", "arguments": "not json"}}, # Bad JSON
    {"id": "call_1", "function": {"name": "tool", "arguments": "[1, 2]"}}, # Args not a dict
])
async def test_malformed_tool_calls_are_skipped(processor, mock_context, bad_call):
    # Arrange
    tool_call_payload = {
        "tool_calls": [
            bad_call,
            {
                "id": "call_good",
                "type": "function",
                "function": {"name": "good_tool", "arguments": "{}"}
            }
        ]
    }
    # Embed the JSON payload in some conversational text
    response_content = f"Okay, I see one valid call and one that seems incorrect. I will proceed with the valid one. {json.dumps(tool_call_payload)}"
    response = CompleteResponse(content=response_content)
    event = LLMCompleteResponseReceivedEvent(complete_response=response)

    # Act
    result = await processor.process_response(response, mock_context, event)

    # Assert
    assert result is True # Should still process the good call
    mock_context.input_event_queues.enqueue_tool_invocation_request.assert_awaited_once()
    enqueued_event: PendingToolInvocationEvent = mock_context.input_event_queues.enqueue_tool_invocation_request.call_args[0][0]
    assert enqueued_event.tool_invocation.name == "good_tool"
    assert enqueued_event.tool_invocation.id == "call_good"
