# file: autobyteus/tests/unit_tests/agent/llm_response_processor/test_gemini_json_tool_usage_processor.py
import pytest
import json
from unittest.mock import MagicMock, AsyncMock

from autobyteus.agent.llm_response_processor import GeminiJsonToolUsageProcessor
from autobyteus.agent.context import AgentContext
from autobyteus.agent.events import LLMCompleteResponseReceivedEvent, PendingToolInvocationEvent
from autobyteus.llm.utils.response_types import CompleteResponse

@pytest.fixture
def processor() -> GeminiJsonToolUsageProcessor:
    return GeminiJsonToolUsageProcessor()

@pytest.fixture
def mock_context() -> MagicMock:
    context = MagicMock(spec=AgentContext)
    context.agent_id = "gemini_test_agent"
    context.input_event_queues = AsyncMock()
    context.input_event_queues.enqueue_tool_invocation_request = AsyncMock()
    return context

@pytest.mark.asyncio
async def test_process_single_valid_tool_call_in_markdown(processor, mock_context):
    # Arrange
    response_text = 'Okay, I will search for that.\n```json\n{"name": "search_web", "args": {"query": "latest AI news"}}\n```'
    response = CompleteResponse(content=response_text)
    event = LLMCompleteResponseReceivedEvent(complete_response=response)

    # Act
    result = await processor.process_response(response, mock_context, event)

    # Assert
    assert result is True
    mock_context.input_event_queues.enqueue_tool_invocation_request.assert_awaited_once()
    enqueued_event: PendingToolInvocationEvent = mock_context.input_event_queues.enqueue_tool_invocation_request.call_args[0][0]
    assert enqueued_event.tool_invocation.name == "search_web"
    assert enqueued_event.tool_invocation.arguments == {"query": "latest AI news"}

@pytest.mark.asyncio
async def test_process_multiple_tool_calls_in_list(processor, mock_context):
    # Arrange
    response_text = '''
    I need to perform two actions.
    ```json
    [
        {"name": "get_file_content", "args": {"path": "/path/to/file.txt"}},
        {"name": "analyze_sentiment", "args": {"text": "This is great!"}}
    ]
    ```
    '''
    response = CompleteResponse(content=response_text)
    event = LLMCompleteResponseReceivedEvent(complete_response=response)

    # Act
    result = await processor.process_response(response, mock_context, event)

    # Assert
    assert result is True
    assert mock_context.input_event_queues.enqueue_tool_invocation_request.await_count == 2

    # Check first call
    first_call_event: PendingToolInvocationEvent = mock_context.input_event_queues.enqueue_tool_invocation_request.await_args_list[0][0][0]
    assert first_call_event.tool_invocation.name == "get_file_content"
    
    # Check second call
    second_call_event: PendingToolInvocationEvent = mock_context.input_event_queues.enqueue_tool_invocation_request.await_args_list[1][0][0]
    assert second_call_event.tool_invocation.name == "analyze_sentiment"
    assert second_call_event.tool_invocation.arguments == {"text": "This is great!"}

@pytest.mark.asyncio
@pytest.mark.parametrize("bad_response", [
    "Just some text, no JSON.",
    '```json\n{"name": "tool_one"}\n```', # Missing 'args'
    '```json\n{"args": {"p": 1}}\n```', # Missing 'name'
    '```json\n{"name": "bad_args", "args": "not a dict"}\n```',
    # REMOVED: '{"name": "no_code_block", "args": {}}' - This is a valid case tested separately.
])
async def test_malformed_or_incomplete_tool_calls(processor, mock_context, bad_response):
    # Arrange
    response = CompleteResponse(content=bad_response)
    event = LLMCompleteResponseReceivedEvent(complete_response=response)
    
    # Act
    result = await processor.process_response(response, mock_context, event)

    # Assert
    assert result is False
    mock_context.input_event_queues.enqueue_tool_invocation_request.assert_not_awaited()

@pytest.mark.asyncio
async def test_raw_json_without_markdown_is_valid(processor, mock_context):
    """
    Tests that a raw, clean JSON string without markdown is still processed correctly.
    This was previously misplaced in the "malformed" test.
    """
    # Arrange
    response_text = '{"name": "raw_json_tool", "args": {"is_raw": true}}'
    response = CompleteResponse(content=response_text)
    event = LLMCompleteResponseReceivedEvent(complete_response=response)

    # Act
    result = await processor.process_response(response, mock_context, event)

    # Assert
    assert result is True
    mock_context.input_event_queues.enqueue_tool_invocation_request.assert_awaited_once()
    enqueued_event: PendingToolInvocationEvent = mock_context.input_event_queues.enqueue_tool_invocation_request.call_args[0][0]
    assert enqueued_event.tool_invocation.name == "raw_json_tool"
    assert enqueued_event.tool_invocation.arguments == {"is_raw": True}
