import pytest
import re 
from unittest.mock import MagicMock, AsyncMock, patch

from autobyteus.agent.llm_response_processor.xml_tool_usage_processor import XmlToolUsageProcessor
from autobyteus.agent.context import AgentContext
from autobyteus.agent.events import AgentInputEventQueueManager, LLMCompleteResponseReceivedEvent
from autobyteus.agent.events import PendingToolInvocationEvent
from autobyteus.agent.tool_invocation import ToolInvocation
from autobyteus.agent.context.agent_config import AgentConfig
from autobyteus.llm.utils.response_types import CompleteResponse

@pytest.fixture
def xml_processor() -> XmlToolUsageProcessor:
    """Fixture for XmlToolUsageProcessor instance."""
    return XmlToolUsageProcessor()

@pytest.fixture
def mock_agent_config() -> MagicMock:
    """Fixture for a mock AgentConfig."""
    mock_conf = MagicMock(spec=AgentConfig)
    mock_conf.name = "xml_test_config"
    mock_conf.llm_response_processors = [XmlToolUsageProcessor()]
    return mock_conf

@pytest.fixture
def mock_input_event_queues() -> AsyncMock:
    """Fixture for mock AgentInputEventQueueManager."""
    queues = AsyncMock(spec=AgentInputEventQueueManager)
    queues.enqueue_tool_invocation_request = AsyncMock()
    return queues

@pytest.fixture
def mock_agent_context(mock_agent_config: MagicMock, mock_input_event_queues: AsyncMock) -> MagicMock:
    """Fixture for a mock AgentContext."""
    context = MagicMock(spec=AgentContext)
    context.agent_id = "xml_test_agent_001"
    context.config = mock_agent_config
    context.input_event_queues = mock_input_event_queues 
    context.tool_instances = {} 
    context.llm_instance = MagicMock()
    return context

@pytest.mark.asyncio
async def test_valid_xml_command_parses_correctly(
    xml_processor: XmlToolUsageProcessor,
    mock_agent_context: MagicMock
):
    response_text = """
    Some text before.
    <command name="SearchTool">
        <arg name="query">best sci-fi movies</arg>
        <arg name="limit">5</arg>
    </command>
    Some text after.
    """
    expected_tool_invocation = ToolInvocation(
        name="SearchTool",
        arguments={"query": "best sci-fi movies", "limit": "5"}
    )
    
    complete_response = CompleteResponse(content=response_text)
    triggering_event = LLMCompleteResponseReceivedEvent(complete_response=complete_response)
    result = await xml_processor.process_response(
        response=complete_response,
        context=mock_agent_context,
        triggering_event=triggering_event
    )

    assert result is True
    mock_agent_context.input_event_queues.enqueue_tool_invocation_request.assert_awaited_once()
    
    call_args = mock_agent_context.input_event_queues.enqueue_tool_invocation_request.call_args
    enqueued_event: PendingToolInvocationEvent = call_args[0][0]
    assert isinstance(enqueued_event, PendingToolInvocationEvent)
    assert enqueued_event.tool_invocation.name == expected_tool_invocation.name
    assert enqueued_event.tool_invocation.arguments == expected_tool_invocation.arguments
    assert isinstance(enqueued_event.tool_invocation.id, str)


@pytest.mark.asyncio
async def test_response_without_xml_command(
    xml_processor: XmlToolUsageProcessor,
    mock_agent_context: MagicMock
):
    response_text = "This is a plain text response without any command."
    complete_response = CompleteResponse(content=response_text)
    triggering_event = LLMCompleteResponseReceivedEvent(complete_response=complete_response)
    result = await xml_processor.process_response(
        response=complete_response,
        context=mock_agent_context,
        triggering_event=triggering_event
    )

    assert result is False
    mock_agent_context.input_event_queues.enqueue_tool_invocation_request.assert_not_awaited()

@pytest.mark.asyncio
async def test_malformed_xml_command(
    xml_processor: XmlToolUsageProcessor,
    mock_agent_context: MagicMock
):
    response_text = "<command name='BrokenTool'><arg name='p1'>v1</arg an_error_here <arg name='p2'>v2</arg></command>"
    
    with patch('autobyteus.agent.llm_response_processor.xml_tool_usage_processor.logger') as mock_logger:
        complete_response = CompleteResponse(content=response_text)
        triggering_event = LLMCompleteResponseReceivedEvent(complete_response=complete_response)
        result = await xml_processor.process_response(
            response=complete_response,
            context=mock_agent_context,
            triggering_event=triggering_event
        )
    
    assert result is False
    mock_agent_context.input_event_queues.enqueue_tool_invocation_request.assert_not_awaited()
    assert any("XML parsing error" in call_args[0][0] for call_args in mock_logger.debug.call_args_list), \
        "Expected 'XML parsing error' log message not found."


@pytest.mark.asyncio
async def test_xml_command_missing_name_attribute(
    xml_processor: XmlToolUsageProcessor,
    mock_agent_context: MagicMock
):
    response_text = "<command><arg name='query'>test</arg></command>"
    
    with patch('autobyteus.agent.llm_response_processor.xml_tool_usage_processor.logger') as mock_logger:
        complete_response = CompleteResponse(content=response_text)
        triggering_event = LLMCompleteResponseReceivedEvent(complete_response=complete_response)
        result = await xml_processor.process_response(
            response=complete_response,
            context=mock_agent_context,
            triggering_event=triggering_event
        )

    assert result is False
    mock_agent_context.input_event_queues.enqueue_tool_invocation_request.assert_not_awaited()
    mock_logger.warning.assert_called_once()
    assert "'name' attribute is missing or empty" in mock_logger.warning.call_args[0][0]


@pytest.mark.asyncio
async def test_xml_with_special_characters_in_args(
    xml_processor: XmlToolUsageProcessor,
    mock_agent_context: MagicMock
):
    response_text_escaped = '<command name="SpecialTool"><arg name="param">A &amp; B &lt; C &gt; D</arg></command>'
    expected_args_escaped = {"param": "A & B < C > D"}

    complete_response_esc = CompleteResponse(content=response_text_escaped)
    triggering_event_esc = LLMCompleteResponseReceivedEvent(complete_response=complete_response_esc)
    result = await xml_processor.process_response(
        response=complete_response_esc,
        context=mock_agent_context,
        triggering_event=triggering_event_esc
    )

    assert result is True
    call_args = mock_agent_context.input_event_queues.enqueue_tool_invocation_request.call_args[0][0]
    assert call_args.tool_invocation.arguments == expected_args_escaped
    mock_agent_context.input_event_queues.enqueue_tool_invocation_request.reset_mock()

    response_text_unescaped = '<command name="SpecialTool"><arg name="param">A & B < C > D</arg></command>'
    expected_args_unescaped = {"param": "A & B < C > D"} 

    complete_response_unesc = CompleteResponse(content=response_text_unescaped)
    triggering_event_unesc = LLMCompleteResponseReceivedEvent(complete_response=complete_response_unesc)
    result_unescaped = await xml_processor.process_response(
        response=complete_response_unesc,
        context=mock_agent_context,
        triggering_event=triggering_event_unesc
    )

    assert result_unescaped is True
    call_args_unescaped = mock_agent_context.input_event_queues.enqueue_tool_invocation_request.call_args[0][0]
    assert call_args_unescaped.tool_invocation.arguments == expected_args_unescaped

@pytest.mark.asyncio
async def test_xml_with_cdata_in_args(
    xml_processor: XmlToolUsageProcessor,
    mock_agent_context: MagicMock
):
    response_text = """
    <command name="CDATATool">
        <arg name="script"><![CDATA[function greet() { if (a < b && b > c) { console.log("Hello & World"); } }]]></arg>
    </command>
    """
    expected_arguments = {
        "script": 'function greet() { if (a < b && b > c) { console.log("Hello & World"); } }'
    }

    complete_response = CompleteResponse(content=response_text)
    triggering_event = LLMCompleteResponseReceivedEvent(complete_response=complete_response)
    result = await xml_processor.process_response(
        response=complete_response,
        context=mock_agent_context,
        triggering_event=triggering_event
    )

    assert result is True
    mock_agent_context.input_event_queues.enqueue_tool_invocation_request.assert_awaited_once()
    call_args = mock_agent_context.input_event_queues.enqueue_tool_invocation_request.call_args[0][0]
    assert call_args.tool_invocation.arguments == expected_arguments

@pytest.mark.asyncio
async def test_xml_with_empty_arguments_tag_value(
    xml_processor: XmlToolUsageProcessor,
    mock_agent_context: MagicMock
):
    response_text = '<command name="EmptyArgTool"><arg name="param1"></arg><arg name="param2">value2</arg></command>'
    expected_arguments = {"param1": "", "param2": "value2"}

    complete_response = CompleteResponse(content=response_text)
    triggering_event = LLMCompleteResponseReceivedEvent(complete_response=complete_response)
    result = await xml_processor.process_response(
        response=complete_response,
        context=mock_agent_context,
        triggering_event=triggering_event
    )

    assert result is True
    mock_agent_context.input_event_queues.enqueue_tool_invocation_request.assert_awaited_once()
    call_args = mock_agent_context.input_event_queues.enqueue_tool_invocation_request.call_args[0][0]
    assert call_args.tool_invocation.arguments == expected_arguments

@pytest.mark.asyncio
async def test_xml_command_with_no_args(
    xml_processor: XmlToolUsageProcessor,
    mock_agent_context: MagicMock
):
    response_text = '<command name="NoArgTool"></command>'
    expected_arguments = {}

    complete_response = CompleteResponse(content=response_text)
    triggering_event = LLMCompleteResponseReceivedEvent(complete_response=complete_response)
    result = await xml_processor.process_response(
        response=complete_response,
        context=mock_agent_context,
        triggering_event=triggering_event
    )

    assert result is True
    mock_agent_context.input_event_queues.enqueue_tool_invocation_request.assert_awaited_once()
    call_args = mock_agent_context.input_event_queues.enqueue_tool_invocation_request.call_args[0][0]
    assert call_args.tool_invocation.name == "NoArgTool"
    assert call_args.tool_invocation.arguments == expected_arguments

@pytest.mark.asyncio
async def test_xml_command_tag_case_insensitivity_in_regex(
    xml_processor: XmlToolUsageProcessor,
    mock_agent_context: MagicMock
):
    response_text = '<COMMAND name="CaseTestTool"><arg name="data">test</arg></COMMAND>'
    
    complete_response = CompleteResponse(content=response_text)
    triggering_event = LLMCompleteResponseReceivedEvent(complete_response=complete_response)
    result = await xml_processor.process_response(
        response=complete_response,
        context=mock_agent_context,
        triggering_event=triggering_event
    )
    
    assert result is True
    mock_agent_context.input_event_queues.enqueue_tool_invocation_request.assert_awaited_once()
    call_args = mock_agent_context.input_event_queues.enqueue_tool_invocation_request.call_args[0][0]
    assert call_args.tool_invocation.name == "CaseTestTool"
    assert call_args.tool_invocation.arguments == {"data": "test"}

@pytest.mark.asyncio
async def test_xml_complex_arg_content_is_stringified(
    xml_processor: XmlToolUsageProcessor,
    mock_agent_context: MagicMock
):
    response_text = """
    <command name="ComplexArgTool">
        <arg name="details">
            <item><id>1</id><value>Apple</value></item>
            <item><id>2</id><value>Banana</value></item>
        </arg>
    </command>
    """
    
    complete_response = CompleteResponse(content=response_text)
    triggering_event = LLMCompleteResponseReceivedEvent(complete_response=complete_response)
    result = await xml_processor.process_response(
        response=complete_response,
        context=mock_agent_context,
        triggering_event=triggering_event
    )
    
    assert result is True 
    call_args = mock_agent_context.input_event_queues.enqueue_tool_invocation_request.call_args[0][0]
    actual_arg_value = call_args.tool_invocation.arguments["details"]

    def normalize_xml_string(s):
        return re.sub(r'\s+', ' ', s).strip() 
    
    expected_value_from_itertext = "1Apple2Banana"
    assert normalize_xml_string(actual_arg_value) == normalize_xml_string(expected_value_from_itertext)
