# file: autobyteus/tests/unit_tests/agent/llm_response_processor/test_default_json_tool_usage_processor.py
import pytest
import json
from unittest.mock import MagicMock, AsyncMock, patch

from autobyteus.agent.llm_response_processor.default_json_tool_usage_processor import DefaultJsonToolUsageProcessor
from autobyteus.agent.context import AgentContext
from autobyteus.agent.events import LLMCompleteResponseReceivedEvent, PendingToolInvocationEvent
from autobyteus.llm.utils.response_types import CompleteResponse

@pytest.fixture
def processor() -> DefaultJsonToolUsageProcessor:
    """Fixture for DefaultJsonToolUsageProcessor instance."""
    return DefaultJsonToolUsageProcessor()

@pytest.fixture
def mock_context() -> MagicMock:
    """Fixture for a mock AgentContext."""
    context = MagicMock(spec=AgentContext)
    context.agent_id = "default_json_test_agent"
    context.input_event_queues = AsyncMock()
    context.input_event_queues.enqueue_tool_invocation_request = AsyncMock()
    return context

@pytest.mark.asyncio
@pytest.mark.parametrize("response_text, expected_tool_name, expected_arguments", [
    # Simple format
    ('{"name": "MyTool", "arguments": {"param1": "value1"}}', "MyTool", {"param1": "value1"}),
    # OpenAI-like format
    ('{"tool_calls": [{"id": "call_123", "type": "function", "function": {"name": "OpenAITool", "arguments": "{\\"key\\": \\"val\\"}"}}]}', "OpenAITool", {"key": "val"}),
    # Gemini-like format
    ('{"name": "GeminiTool", "args": {"query": "test"}}', "GeminiTool", {"query": "test"}),
    # In markdown block
    ('```json\n{"name": "CodeTool", "arguments": {"data": [1, 2]}}\n```', "CodeTool", {"data": [1, 2]}),
    # In a list
    ('[{"name": "ListTool", "arguments": {"item": "A"}}]', "ListTool", {"item": "A"}),
    # Noisy text with JSON at the end
    ('Some thinking... and then the action: {"name": "TrailingTool", "arguments": {"p": 1}}', "TrailingTool", {"p": 1}),
])
async def test_valid_json_variants_are_parsed(
    processor: DefaultJsonToolUsageProcessor,
    mock_context: MagicMock,
    response_text: str,
    expected_tool_name: str,
    expected_arguments: dict
):
    """Tests that the best-effort parser handles various valid JSON formats."""
    # Arrange
    response = CompleteResponse(content=response_text)
    event = LLMCompleteResponseReceivedEvent(complete_response=response)

    # Act
    result = await processor.process_response(response, mock_context, event)

    # Assert
    assert result is True
    mock_context.input_event_queues.enqueue_tool_invocation_request.assert_awaited_once()
    
    enqueued_event: PendingToolInvocationEvent = mock_context.input_event_queues.enqueue_tool_invocation_request.call_args[0][0]
    assert enqueued_event.tool_invocation.name == expected_tool_name
    assert enqueued_event.tool_invocation.arguments == expected_arguments

@pytest.mark.asyncio
@pytest.mark.parametrize("response_text", [
    "This is just plain text with no JSON.",
    "{'tool_name': 'MyTool'}",  # Invalid JSON (single quotes)
    "```json\n{'invalid': 'json'}\n```", # Invalid JSON in markdown
    "{\"name\": \"MissingArgs\"}", # Missing arguments/args key
    "{\"arguments\": {\"param\": 1}}", # Missing name key
    "[]", # Empty list
    "[{\"not_a_tool_call\": true}]", # List with incorrect object structure
])
async def test_invalid_or_non_tool_json(
    processor: DefaultJsonToolUsageProcessor,
    mock_context: MagicMock,
    response_text: str
):
    """Tests that invalid JSON or JSON not matching a tool call structure is ignored."""
    # Arrange
    response = CompleteResponse(content=response_text)
    event = LLMCompleteResponseReceivedEvent(complete_response=response)

    # Act
    result = await processor.process_response(response, mock_context, event)

    # Assert
    assert result is False
    mock_context.input_event_queues.enqueue_tool_invocation_request.assert_not_awaited()

@pytest.mark.asyncio
async def test_empty_json_object_is_ignored(
    processor: DefaultJsonToolUsageProcessor,
    mock_context: MagicMock
):
    """Tests that an empty JSON object does not trigger a tool call."""
    # Arrange
    response = CompleteResponse(content="{}")
    event = LLMCompleteResponseReceivedEvent(complete_response=response)

    # Act
    result = await processor.process_response(response, mock_context, event)

    # Assert
    assert result is False
    mock_context.input_event_queues.enqueue_tool_invocation_request.assert_not_awaited()
