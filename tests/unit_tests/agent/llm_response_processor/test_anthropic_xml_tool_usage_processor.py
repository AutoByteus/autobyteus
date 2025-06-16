# file: autobyteus/tests/unit_tests/agent/llm_response_processor/test_anthropic_xml_tool_usage_processor.py
import pytest
from unittest.mock import MagicMock, AsyncMock

from autobyteus.agent.llm_response_processor import AnthropicXmlToolUsageProcessor
from autobyteus.agent.context import AgentContext
from autobyteus.agent.events import LLMCompleteResponseReceivedEvent, PendingToolInvocationEvent
from autobyteus.llm.utils.response_types import CompleteResponse

@pytest.fixture
def processor() -> AnthropicXmlToolUsageProcessor:
    return AnthropicXmlToolUsageProcessor()

@pytest.fixture
def mock_context() -> MagicMock:
    context = MagicMock(spec=AgentContext)
    context.agent_id = "anthropic_test_agent"
    context.input_event_queues = AsyncMock()
    context.input_event_queues.enqueue_tool_invocation_request = AsyncMock()
    return context

@pytest.mark.asyncio
async def test_process_single_valid_tool_call(processor, mock_context):
    # Arrange
    response_text = """
    I think I should use a tool for this. Here is the tool call:
    <tool_calls>
        <tool_call name="get_stock_price" id="tool_123">
            <arguments>
                <arg name="ticker_symbol">GOOG</arg>
            </arguments>
        </tool_call>
    </tool_calls>
    """
    response = CompleteResponse(content=response_text)
    event = LLMCompleteResponseReceivedEvent(complete_response=response)

    # Act
    result = await processor.process_response(response, mock_context, event)

    # Assert
    assert result is True
    mock_context.input_event_queues.enqueue_tool_invocation_request.assert_awaited_once()
    enqueued_event: PendingToolInvocationEvent = mock_context.input_event_queues.enqueue_tool_invocation_request.call_args[0][0]
    assert enqueued_event.tool_invocation.id == "tool_123"
    assert enqueued_event.tool_invocation.name == "get_stock_price"
    assert enqueued_event.tool_invocation.arguments == {"ticker_symbol": "GOOG"}

@pytest.mark.asyncio
async def test_process_multiple_valid_tool_calls(processor, mock_context):
    # Arrange
    response_text = """
    <tool_calls>
        <tool_call name="lookup_user" id="user_lookup_abc">
            <arguments>
                <arg name="email">user@example.com</arg>
            </arguments>
        </tool_call>
        <tool_call name="create_ticket" id="ticket_xyz">
            <arguments>
                <arg name="title">Fix the thing</arg>
                <arg name="priority">high</arg>
            </arguments>
        </tool_call>
    </tool_calls>
    """
    response = CompleteResponse(content=response_text)
    event = LLMCompleteResponseReceivedEvent(complete_response=response)

    # Act
    result = await processor.process_response(response, mock_context, event)

    # Assert
    assert result is True
    assert mock_context.input_event_queues.enqueue_tool_invocation_request.await_count == 2
    
    first_call_event: PendingToolInvocationEvent = mock_context.input_event_queues.enqueue_tool_invocation_request.await_args_list[0][0][0]
    assert first_call_event.tool_invocation.id == "user_lookup_abc"
    assert first_call_event.tool_invocation.name == "lookup_user"
    
    second_call_event: PendingToolInvocationEvent = mock_context.input_event_queues.enqueue_tool_invocation_request.await_args_list[1][0][0]
    assert second_call_event.tool_invocation.id == "ticket_xyz"
    assert second_call_event.tool_invocation.name == "create_ticket"
    assert second_call_event.tool_invocation.arguments == {"title": "Fix the thing", "priority": "high"}

@pytest.mark.asyncio
async def test_no_tool_calls_block(processor, mock_context):
    # Arrange
    response_text = "I have analyzed the request and the answer is 42."
    response = CompleteResponse(content=response_text)
    event = LLMCompleteResponseReceivedEvent(complete_response=response)

    # Act
    result = await processor.process_response(response, mock_context, event)

    # Assert
    assert result is False
    mock_context.input_event_queues.enqueue_tool_invocation_request.assert_not_awaited()

@pytest.mark.asyncio
async def test_malformed_xml_is_handled(processor, mock_context):
    # Arrange
    response_text = "<tool_calls><tool_call name='bad_xml'>...<arguments></tool_call></tool_calls>" # missing closing </arguments>
    response = CompleteResponse(content=response_text)
    event = LLMCompleteResponseReceivedEvent(complete_response=response)

    # Act
    result = await processor.process_response(response, mock_context, event)

    # Assert
    assert result is False
    mock_context.input_event_queues.enqueue_tool_invocation_request.assert_not_awaited()
