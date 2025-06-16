# file: autobyteus/tests/unit_tests/agent/llm_response_processor/test_default_xml_tool_usage_processor.py
import pytest
import re
from unittest.mock import MagicMock, AsyncMock, patch

from autobyteus.agent.llm_response_processor.default_xml_tool_usage_processor import DefaultXmlToolUsageProcessor
from autobyteus.agent.context import AgentContext
from autobyteus.agent.events import LLMCompleteResponseReceivedEvent, PendingToolInvocationEvent
from autobyteus.llm.utils.response_types import CompleteResponse

@pytest.fixture
def processor() -> DefaultXmlToolUsageProcessor:
    """Fixture for DefaultXmlToolUsageProcessor instance."""
    return DefaultXmlToolUsageProcessor()

@pytest.fixture
def mock_context() -> MagicMock:
    """Fixture for a mock AgentContext."""
    context = MagicMock(spec=AgentContext)
    context.agent_id = "default_xml_test_agent"
    context.input_event_queues = AsyncMock()
    context.input_event_queues.enqueue_tool_invocation_request = AsyncMock()
    return context

@pytest.mark.asyncio
async def test_process_single_valid_tool_call(processor, mock_context):
    # Arrange
    response_text = """
    Here is the tool call I'd like to make:
    <tool_calls>
        <tool_call name="search_files" id="call_12345">
            <arguments>
                <arg name="query">customer_report.pdf</arg>
                <arg name="limit">1</arg>
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
    assert enqueued_event.tool_invocation.id == "call_12345"
    assert enqueued_event.tool_invocation.name == "search_files"
    assert enqueued_event.tool_invocation.arguments == {"query": "customer_report.pdf", "limit": "1"}

@pytest.mark.asyncio
async def test_no_tool_calls_block(processor, mock_context):
    # Arrange
    response_text = "This is a simple text response with no tools."
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
    response_text = "<tool_calls><tool_call name='bad_xml'><arg name='p1'>v1</tool_call>" # Missing closing tags
    response = CompleteResponse(content=response_text)
    event = LLMCompleteResponseReceivedEvent(complete_response=response)

    # Act
    result = await processor.process_response(response, mock_context, event)

    # Assert
    assert result is False
    mock_context.input_event_queues.enqueue_tool_invocation_request.assert_not_awaited()

@pytest.mark.asyncio
async def test_xml_with_special_characters_in_args(processor, mock_context):
    # Arrange
    response_text = '<tool_calls><tool_call name="SpecialTool"><arguments><arg name="param">A &amp; B &lt; C &gt; D</arg></arguments></tool_call></tool_calls>'
    expected_args = {"param": "A & B < C > D"}

    response = CompleteResponse(content=response_text)
    event = LLMCompleteResponseReceivedEvent(complete_response=response)
    
    # Act
    result = await processor.process_response(response, mock_context, event)

    # Assert
    assert result is True
    call_args = mock_context.input_event_queues.enqueue_tool_invocation_request.call_args[0][0]
    assert call_args.tool_invocation.arguments == expected_args

@pytest.mark.asyncio
async def test_xml_with_cdata_in_args(processor, mock_context):
    # Arrange
    response_text = """
    <tool_calls>
        <tool_call name="CodeExecutor">
            <arguments>
                <arg name="code"><![CDATA[if (x < 10 && y > 5) { console.log("<Hello & World>"); }]]></arg>
            </arguments>
        </tool_call>
    </tool_calls>
    """
    expected_arguments = {
        "code": 'if (x < 10 && y > 5) { console.log("<Hello & World>"); }'
    }

    response = CompleteResponse(content=response_text)
    event = LLMCompleteResponseReceivedEvent(complete_response=response)
    
    # Act
    result = await processor.process_response(response, mock_context, event)

    # Assert
    assert result is True
    call_args = mock_context.input_event_queues.enqueue_tool_invocation_request.call_args[0][0]
    assert call_args.tool_invocation.arguments == expected_arguments

@pytest.mark.asyncio
async def test_xml_command_with_no_args(processor, mock_context):
    # Arrange
    response_text = '<tool_calls><tool_call name="get_current_time"></tool_call></tool_calls>'
    expected_arguments = {}

    response = CompleteResponse(content=response_text)
    event = LLMCompleteResponseReceivedEvent(complete_response=response)
    
    # Act
    result = await processor.process_response(response, mock_context, event)

    # Assert
    assert result is True
    call_args = mock_context.input_event_queues.enqueue_tool_invocation_request.call_args[0][0]
    assert call_args.tool_invocation.name == "get_current_time"
    assert call_args.tool_invocation.arguments == expected_arguments
