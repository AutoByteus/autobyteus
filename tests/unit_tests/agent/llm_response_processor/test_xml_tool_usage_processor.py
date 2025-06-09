import pytest
import re 
from unittest.mock import MagicMock, AsyncMock, patch

from autobyteus.agent.llm_response_processor.xml_tool_usage_processor import XmlToolUsageProcessor
from autobyteus.agent.context import AgentContext
from autobyteus.agent.events import AgentInputEventQueueManager
from autobyteus.agent.events import PendingToolInvocationEvent
from autobyteus.agent.tool_invocation import ToolInvocation
from autobyteus.agent.registry.agent_specification import AgentSpecification

@pytest.fixture
def xml_processor() -> XmlToolUsageProcessor:
    """Fixture for XmlToolUsageProcessor instance."""
    return XmlToolUsageProcessor()

@pytest.fixture
def mock_agent_specification() -> MagicMock:
    """Fixture for a mock AgentSpecification."""
    mock_spec = MagicMock(spec=AgentSpecification)
    mock_spec.name = "xml_test_specification"
    mock_spec.llm_response_processor_names = ["xml_tool_usage"] 
    return mock_spec

@pytest.fixture
def mock_input_event_queues() -> AsyncMock:
    """Fixture for mock AgentInputEventQueueManager."""
    queues = AsyncMock(spec=AgentInputEventQueueManager)
    queues.enqueue_tool_invocation_request = AsyncMock()
    return queues

@pytest.fixture
def mock_agent_context(mock_agent_specification: MagicMock, mock_input_event_queues: AsyncMock) -> MagicMock:
    """Fixture for a mock AgentContext."""
    context = MagicMock(spec=AgentContext)
    context.agent_id = "xml_test_agent_001"
    context.specification = mock_agent_specification
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

    result = await xml_processor.process_response(response_text, mock_agent_context)

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
    result = await xml_processor.process_response(response_text, mock_agent_context)

    assert result is False
    mock_agent_context.input_event_queues.enqueue_tool_invocation_request.assert_not_awaited()

@pytest.mark.asyncio
async def test_malformed_xml_command(
    xml_processor: XmlToolUsageProcessor,
    mock_agent_context: MagicMock
):
    response_text = "<command name='BrokenTool'><arg name='p1'>v1</arg an_error_here <arg name='p2'>v2</arg></command>"
    
    with patch('autobyteus.agent.llm_response_processor.xml_tool_usage_processor.logger') as mock_logger:
        result = await xml_processor.process_response(response_text, mock_agent_context)
    
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
        result = await xml_processor.process_response(response_text, mock_agent_context)

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

    result = await xml_processor.process_response(response_text_escaped, mock_agent_context)
    assert result is True
    call_args = mock_agent_context.input_event_queues.enqueue_tool_invocation_request.call_args[0][0]
    assert call_args.tool_invocation.arguments == expected_args_escaped
    mock_agent_context.input_event_queues.enqueue_tool_invocation_request.reset_mock()

    response_text_unescaped = '<command name="SpecialTool"><arg name="param">A & B < C > D</arg></command>'
    expected_args_unescaped = {"param": "A & B < C > D"} 

    result_unescaped = await xml_processor.process_response(response_text_unescaped, mock_agent_context)
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
    result = await xml_processor.process_response(response_text, mock_agent_context)

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

    result = await xml_processor.process_response(response_text, mock_agent_context)

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

    result = await xml_processor.process_response(response_text, mock_agent_context)

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
    
    result = await xml_processor.process_response(response_text, mock_agent_context)
    
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
    
    result = await xml_processor.process_response(response_text.replace("name=\"details\"", "name='details'"), mock_agent_context) 
    
    assert result is True 
    call_args = mock_agent_context.input_event_queues.enqueue_tool_invocation_request.call_args[0][0]
    actual_arg_value = call_args.tool_invocation.arguments["details"]

    def normalize_xml_string(s):
        return re.sub(r'\s+', ' ', s).strip() 
    
    expected_value_from_itertext = "1Apple2Banana"
    assert normalize_xml_string(actual_arg_value) == normalize_xml_string(expected_value_from_itertext)
