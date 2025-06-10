import pytest
import json
from unittest.mock import MagicMock, AsyncMock, patch

from autobyteus.agent.llm_response_processor.json_tool_usage_processor import JsonToolUsageProcessor
from autobyteus.agent.context import AgentContext
from autobyteus.agent.events import AgentInputEventQueueManager
from autobyteus.agent.events import PendingToolInvocationEvent
from autobyteus.agent.tool_invocation import ToolInvocation
from autobyteus.agent.context.agent_config import AgentConfig

@pytest.fixture
def json_processor() -> JsonToolUsageProcessor:
    """Fixture for JsonToolUsageProcessor instance."""
    return JsonToolUsageProcessor()

@pytest.fixture
def mock_agent_config() -> MagicMock:
    """Fixture for a mock AgentConfig."""
    mock_conf = MagicMock(spec=AgentConfig)
    mock_conf.name = "json_test_config"
    mock_conf.llm_response_processors = [JsonToolUsageProcessor()]
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
    context.agent_id = "json_test_agent_001"
    context.config = mock_agent_config
    context.input_event_queues = mock_input_event_queues 
    context.tool_instances = {}
    context.llm_instance = MagicMock()
    return context

@pytest.mark.asyncio
@pytest.mark.parametrize("response_text, expected_tool_name, expected_arguments", [
    ('{"tool_name": "MyTool", "arguments": {"param1": "value1"}}', "MyTool", {"param1": "value1"}),
    ('```json\n{"tool_name": "CodeTool", "arguments": {"data": [1, 2]}}\n```', "CodeTool", {"data": [1, 2]}),
    ('{"name": "AltNameTool", "arguments": {"arg": true}}', "AltNameTool", {"arg": True}),
    ('{"tool_call": {"function": {"name": "OpenAITool", "arguments": "{\\"key\\": \\"val\\"}"}}}', "OpenAITool", {"key": "val"}),
    ('{"tool_call": {"function": {"name": "OpenAIObjTool", "arguments": {"key": "valObj"}}}}', "OpenAIObjTool", {"key": "valObj"}),
    ('[{"tool_name": "ListTool", "arguments": {"item": "A"}}]', "ListTool", {"item": "A"}),
    ('[{"non_tool": "data"}, {"tool_name": "SecondInList", "arguments": {}}]', "SecondInList", {}),
    ('Some thinking... and then the action: {"tool_name": "TrailingTool", "arguments": {"p": 1}}', "TrailingTool", {"p": 1}),
    ('{"command": {"name": "CommandKeyTool", "arguments": {"cmd_arg": "test"}}}', "CommandKeyTool", {"cmd_arg": "test"}),
    ('{"tool_name": "NestedJsonArgs", "arguments": {"config": "{\\"setting\\": true}"}}', "NestedJsonArgs", {"config": {"setting": True}}),
])
async def test_valid_json_variants_parse_correctly(
    json_processor: JsonToolUsageProcessor,
    mock_agent_context: MagicMock,
    response_text: str,
    expected_tool_name: str,
    expected_arguments: dict
):
    result = await json_processor.process_response(response_text, mock_agent_context)

    assert result is True
    mock_agent_context.input_event_queues.enqueue_tool_invocation_request.assert_awaited_once()
    
    call_args = mock_agent_context.input_event_queues.enqueue_tool_invocation_request.call_args
    enqueued_event: PendingToolInvocationEvent = call_args[0][0]
    assert isinstance(enqueued_event, PendingToolInvocationEvent)
    assert enqueued_event.tool_invocation.name == expected_tool_name
    assert enqueued_event.tool_invocation.arguments == expected_arguments

@pytest.mark.asyncio
@pytest.mark.parametrize("response_text", [
    "This is plain text.",
    "No JSON here, just words.",
    "{'tool_name': 'MyTool', 'arguments': 'oops single quotes'}", 
    "```json\n{'invalid': 'json'}\n```", 
    "{\"tool_name\": \"MissingArgs\"}", 
    "{\"arguments\": {\"param\": 1}}", 
    "{\"tool_name\": null, \"arguments\": {}}", 
    "[]", 
    "[{\"not_a_tool_call\": true}]", 
    "{\"tool_name\": \"BadArgs\", \"arguments\": \"not a json string or dict\"}", 
    "{\"tool_name\": \"NumArgs\", \"arguments\": 123}", 
])
async def test_invalid_or_no_json_command(
    json_processor: JsonToolUsageProcessor,
    mock_agent_context: MagicMock,
    response_text: str
):
    with patch('autobyteus.agent.llm_response_processor.json_tool_usage_processor.logger') as mock_logger:
        result = await json_processor.process_response(response_text, mock_agent_context)

    assert result is False
    mock_agent_context.input_event_queues.enqueue_tool_invocation_request.assert_not_awaited()

@pytest.mark.asyncio
async def test_json_with_null_arguments_field(
    json_processor: JsonToolUsageProcessor,
    mock_agent_context: MagicMock
):
    response_text = '{"tool_name": "NullArgsTool", "arguments": null}'
    expected_tool_name = "NullArgsTool"
    expected_arguments = {} 

    result = await json_processor.process_response(response_text, mock_agent_context)

    assert result is True
    mock_agent_context.input_event_queues.enqueue_tool_invocation_request.assert_awaited_once()
    call_args = mock_agent_context.input_event_queues.enqueue_tool_invocation_request.call_args[0][0]
    assert call_args.tool_invocation.name == expected_tool_name
    assert call_args.tool_invocation.arguments == expected_arguments

@pytest.mark.asyncio
async def test_json_extraction_from_noisy_response(
    json_processor: JsonToolUsageProcessor,
    mock_agent_context: MagicMock
):
    response_text = """
    Okay, I've thought about it.
    Here's my plan:
    1. First, I will do this.
    2. Then, I will do that.
    Finally, I need to use a tool.
    This is some garbage before the JSON { "other_key": "other_value" }
    And here is the actual command: {"tool_name": "ExtractTest", "arguments": {"data": "important"}}
    Maybe some trailing thoughts.
    """
    expected_tool_name = "ExtractTest"
    expected_arguments = {"data": "important"}

    result = await json_processor.process_response(response_text, mock_agent_context)

    assert result is True
    mock_agent_context.input_event_queues.enqueue_tool_invocation_request.assert_awaited_once()
    call_args = mock_agent_context.input_event_queues.enqueue_tool_invocation_request.call_args[0][0]
    assert call_args.tool_invocation.name == expected_tool_name
    assert call_args.tool_invocation.arguments == expected_arguments

@pytest.mark.asyncio
async def test_arguments_parsing_string_vs_dict(
    json_processor: JsonToolUsageProcessor,
    mock_agent_context: MagicMock
):
    response_str_args = '{"tool_name": "StringArgsTool", "arguments": "{\\"param\\": \\"value\\"}"}'
    result_str = await json_processor.process_response(response_str_args, mock_agent_context)
    assert result_str is True
    call_args_str = mock_agent_context.input_event_queues.enqueue_tool_invocation_request.call_args[0][0]
    assert call_args_str.tool_invocation.arguments == {"param": "value"}
    mock_agent_context.input_event_queues.enqueue_tool_invocation_request.reset_mock()

    response_dict_args = '{"tool_name": "DictArgsTool", "arguments": {"param": "value"}}'
    result_dict = await json_processor.process_response(response_dict_args, mock_agent_context)
    assert result_dict is True
    call_args_dict = mock_agent_context.input_event_queues.enqueue_tool_invocation_request.call_args[0][0]
    assert call_args_dict.tool_invocation.arguments == {"param": "value"}

@pytest.mark.asyncio
async def test_empty_json_object_no_action(
    json_processor: JsonToolUsageProcessor,
    mock_agent_context: MagicMock
):
    response_text = "{}"
    result = await json_processor.process_response(response_text, mock_agent_context)
    assert result is False
    mock_agent_context.input_event_queues.enqueue_tool_invocation_request.assert_not_awaited()

@pytest.mark.asyncio
async def test_json_with_non_string_tool_name_no_action(
    json_processor: JsonToolUsageProcessor,
    mock_agent_context: MagicMock
):
    response_text = '{"tool_name": 123, "arguments": {}}'
    result = await json_processor.process_response(response_text, mock_agent_context)
    assert result is False
    mock_agent_context.input_event_queues.enqueue_tool_invocation_request.assert_not_awaited()

    response_text_bool = '{"tool_name": true, "arguments": {}}' 
    result_bool = await json_processor.process_response(response_text_bool, mock_agent_context)
    assert result_bool is False 
    mock_agent_context.input_event_queues.enqueue_tool_invocation_request.assert_not_awaited()
