# file: autobyteus/tests/unit_tests/tools/usage/parsers/test_openai_json_tool_usage_parser.py
import pytest
import json
from autobyteus.tools.usage.parsers import OpenAiJsonToolUsageParser
from autobyteus.llm.utils.response_types import CompleteResponse
from autobyteus.agent.tool_invocation import ToolInvocation

@pytest.fixture
def parser() -> OpenAiJsonToolUsageParser:
    return OpenAiJsonToolUsageParser()

# --- REGRESSION TESTS FOR ORIGINAL FUNCTIONALITY ---

def test_parse_single_valid_tool_call_full_format(parser: OpenAiJsonToolUsageParser):
    # Arrange
    tool_call_payload = {
        "tool_calls": [{"id": "call_abc123", "type": "function", "function": {"name": "get_weather", "arguments": '{"location": "Boston, MA"}'}}]
    }
    response = CompleteResponse(content=json.dumps(tool_call_payload))

    # Act
    invocations = parser.parse(response)

    # Assert
    assert len(invocations) == 1
    invocation = invocations[0]
    assert isinstance(invocation, ToolInvocation)
    assert invocation.id == "call_abc123"
    assert invocation.name == "get_weather"
    assert invocation.arguments == {"location": "Boston, MA"}

def test_parse_multiple_valid_tool_calls(parser: OpenAiJsonToolUsageParser):
    # Arrange
    tool_call_payload = {
        "tool_calls": [
            {"id": "call_abc123", "type": "function", "function": {"name": "get_weather", "arguments": '{"location": "Boston, MA"}'}},
            {"id": "call_def456", "type": "function", "function": {"name": "send_email", "arguments": '{"to": "test@example.com", "subject": "Hello"}'}}
        ]
    }
    response = CompleteResponse(content=json.dumps(tool_call_payload))

    # Act
    invocations = parser.parse(response)

    # Assert
    assert len(invocations) == 2
    assert invocations[0].id == "call_abc123"
    assert invocations[1].id == "call_def456"

@pytest.mark.parametrize("bad_content", [
    "This is just a text response.",
    json.dumps({"tool_calls": None}),
    json.dumps({"some_other_key": [{"id": "call_1"}]}),
    "This is text with an invalid json { 'key': 'val' }",
])
def test_no_or_invalid_tool_calls_in_response(parser: OpenAiJsonToolUsageParser, bad_content: str):
    # Arrange
    response = CompleteResponse(content=bad_content)
    # Act
    invocations = parser.parse(response)
    # Assert
    assert len(invocations) == 0

# --- NEW TESTS FOR ENHANCED FLEXIBILITY ---

def test_parse_simplified_format_from_finetuned_model(parser: OpenAiJsonToolUsageParser):
    # Arrange
    simplified_payload = [
        {"name": "get_stock_price", "arguments": {"ticker": "GOOG"}},
        {"name": "send_notification", "arguments": {"message": "Price is high"}}
    ]
    response = CompleteResponse(content=json.dumps(simplified_payload))
    
    # Act
    invocations = parser.parse(response)

    # Assert
    assert len(invocations) == 2
    assert invocations[0].name == "get_stock_price"
    assert invocations[0].arguments == {"ticker": "GOOG"}
    assert invocations[1].name == "send_notification"
    assert invocations[1].arguments == {"message": "Price is high"}

def test_parse_tool_call_with_missing_id(parser: OpenAiJsonToolUsageParser):
    # Arrange
    payload_no_id = {"tool_calls": [{"type": "function", "function": {"name": "get_weather", "arguments": '{}'}}]}
    response = CompleteResponse(content=json.dumps(payload_no_id))

    # Act
    invocations = parser.parse(response)

    # Assert
    assert len(invocations) == 1
    assert invocations[0].id is not None
    assert invocations[0].id.startswith("call_")

@pytest.mark.parametrize("payload", [
    # Simplified format
    '{"name": "run_query", "arguments": {"sql": "SELECT * FROM users"}}',
    # Full API format
    '{"id": "call_xyz", "type": "function", "function": {"name": "run_query", "arguments": "{\\"sql\\": \\"SELECT * FROM users\\"}"}}'
])
def test_parse_single_tool_call_not_in_list(parser: OpenAiJsonToolUsageParser, payload: str):
    # Arrange
    response = CompleteResponse(content=payload)

    # Act
    invocations = parser.parse(response)

    # Assert
    assert len(invocations) == 1
    assert invocations[0].name == "run_query"
    assert invocations[0].arguments == {"sql": "SELECT * FROM users"}
    if "call_xyz" in payload:
        assert invocations[0].id == "call_xyz"

def test_parse_single_tool_call_not_in_list_function_wrapper(parser: OpenAiJsonToolUsageParser):
    # Arrange
    payload = '{"function": {"name": "run_query", "arguments": "{\\"sql\\": \\"SELECT * FROM users\\"}"}}'
    response = CompleteResponse(content=payload)

    # Act
    invocations = parser.parse(response)

    # Assert
    assert len(invocations) == 1
    assert invocations[0].name == "run_query"
    assert invocations[0].arguments == {"sql": "SELECT * FROM users"}
    assert invocations[0].id.startswith("call_") # ID should be generated

def test_parse_tool_call_under_tools_key(parser: OpenAiJsonToolUsageParser):
    # Arrange
    payload_with_tools_key = {
        "tools": [{"id": "call_abc123", "type": "function", "function": {"name": "get_weather", "arguments": '{"location": "Boston, MA"}'}}]
    }
    response = CompleteResponse(content=json.dumps(payload_with_tools_key))

    # Act
    invocations = parser.parse(response)

    # Assert
    assert len(invocations) == 1
    assert invocations[0].name == "get_weather"

def test_parse_json_from_markdown_block(parser: OpenAiJsonToolUsageParser):
    # Arrange
    content = """
Some preceding text from the model.
```json
{
    "tool_calls": [{
        "id": "call_md123",
        "type": "function",
        "function": {
            "name": "execute_code",
            "arguments": "{\\"code\\": \\"print('hello')\\"}"
        }
    }]
}
```
Some trailing text.
"""
    response = CompleteResponse(content=content)
    
    # Act
    invocations = parser.parse(response)

    # Assert
    assert len(invocations) == 1
    assert invocations[0].id == "call_md123"
    assert invocations[0].name == "execute_code"
    assert invocations[0].arguments == {"code": "print('hello')"}

@pytest.mark.parametrize("arguments_payload", [
    '{"arguments": {}}',
    '{"arguments": null}',
    '{}' # arguments key is missing entirely
])
def test_parse_tool_call_with_no_arguments(parser: OpenAiJsonToolUsageParser, arguments_payload):
    # Arrange
    content = f'[{{"name": "list_files", {arguments_payload.strip("{}")} }}]'
    response = CompleteResponse(content=content)

    # Act
    invocations = parser.parse(response)

    # Assert
    assert len(invocations) == 1
    assert invocations[0].name == "list_files"
    assert invocations[0].arguments == {}
