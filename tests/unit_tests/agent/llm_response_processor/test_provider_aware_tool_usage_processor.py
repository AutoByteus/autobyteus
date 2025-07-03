# file: autobyteus/tests/unit_tests/agent/llm_response_processor/test_provider_aware_tool_usage_processor.py
import pytest
from unittest.mock import MagicMock, AsyncMock, patch

from autobyteus.agent.llm_response_processor import ProviderAwareToolUsageProcessor
from autobyteus.agent.context import AgentContext
from autobyteus.agent.events import LLMCompleteResponseReceivedEvent, PendingToolInvocationEvent
from autobyteus.agent.tool_invocation import ToolInvocation
from autobyteus.llm.utils.response_types import CompleteResponse
from autobyteus.tools.usage.parsers.exceptions import ToolUsageParseException

@pytest.fixture
def mock_context() -> MagicMock:
    """Fixture for a mock AgentContext."""
    context = MagicMock(spec=AgentContext)
    context.agent_id = "test_agent_123"
    context.input_event_queues = AsyncMock()
    context.input_event_queues.enqueue_tool_invocation_request = AsyncMock()
    return context

@pytest.mark.asyncio
@patch('autobyteus.agent.llm_response_processor.provider_aware_tool_usage_processor.ProviderAwareToolUsageParser')
async def test_processor_uses_parser_and_enqueues_events(mock_parser_class, mock_context):
    """
    Tests that the processor uses the parser and enqueues events for each parsed invocation.
    """
    # Arrange
    # Create mock tool invocations that the mock parser will return
    mock_invocations = [
        ToolInvocation(id="call_1", name="tool_one", arguments={"a": 1}),
        ToolInvocation(id="call_2", name="tool_two", arguments={"b": 2}),
    ]
    
    # Configure the mock parser instance
    mock_parser_instance = mock_parser_class.return_value
    mock_parser_instance.parse.return_value = mock_invocations

    # The processor to test
    processor = ProviderAwareToolUsageProcessor()
    
    # Dummy response and event
    response = CompleteResponse(content="some llm response")
    trigger_event = LLMCompleteResponseReceivedEvent(complete_response=response)

    # Act
    result = await processor.process_response(response, mock_context, trigger_event)

    # Assert
    # Verify that the processor indicated it handled the response
    assert result is True
    
    # Verify the parser was instantiated and its `parse` method was called correctly
    mock_parser_class.assert_called_once()
    mock_parser_instance.parse.assert_called_once_with(response, mock_context)
    
    # Verify that an event was enqueued for each invocation returned by the parser
    assert mock_context.input_event_queues.enqueue_tool_invocation_request.await_count == 2
    
    # Check the content of the enqueued events
    first_call_event: PendingToolInvocationEvent = mock_context.input_event_queues.enqueue_tool_invocation_request.await_args_list[0][0][0]
    assert first_call_event.tool_invocation is mock_invocations[0]

    second_call_event: PendingToolInvocationEvent = mock_context.input_event_queues.enqueue_tool_invocation_request.await_args_list[1][0][0]
    assert second_call_event.tool_invocation is mock_invocations[1]

@pytest.mark.asyncio
@patch('autobyteus.agent.llm_response_processor.provider_aware_tool_usage_processor.ProviderAwareToolUsageParser')
async def test_processor_does_nothing_when_parser_returns_empty(mock_parser_class, mock_context):
    """
    Tests that the processor does nothing if the parser finds no tool invocations.
    """
    # Arrange
    # Configure the mock parser to return an empty list
    mock_parser_instance = mock_parser_class.return_value
    mock_parser_instance.parse.return_value = []

    processor = ProviderAwareToolUsageProcessor()
    response = CompleteResponse(content="some llm response")
    trigger_event = LLMCompleteResponseReceivedEvent(complete_response=response)

    # Act
    result = await processor.process_response(response, mock_context, trigger_event)

    # Assert
    # Verify that the processor indicated it did *not* handle the response
    assert result is False
    
    # Verify the parser was still called
    mock_parser_instance.parse.assert_called_once_with(response, mock_context)
    
    # Verify no events were enqueued
    mock_context.input_event_queues.enqueue_tool_invocation_request.assert_not_awaited()

@pytest.mark.asyncio
@patch('autobyteus.agent.llm_response_processor.provider_aware_tool_usage_processor.ProviderAwareToolUsageParser')
async def test_processor_propagates_parsing_exception(mock_parser_class, mock_context):
    """
    Tests that if the parser raises a ToolUsageParseException, the processor re-raises it.
    """
    # Arrange
    mock_parser_instance = mock_parser_class.return_value
    parse_exception = ToolUsageParseException("Failed to parse for testing.")
    mock_parser_instance.parse.side_effect = parse_exception

    processor = ProviderAwareToolUsageProcessor()
    response = CompleteResponse(content="<tool_code>invalid</tool_code>")
    trigger_event = LLMCompleteResponseReceivedEvent(complete_response=response)

    # Act & Assert
    with pytest.raises(ToolUsageParseException) as exc_info:
        await processor.process_response(response, mock_context, trigger_event)

    assert exc_info.value is parse_exception
    mock_context.input_event_queues.enqueue_tool_invocation_request.assert_not_awaited()
