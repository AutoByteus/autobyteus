# file: autobyteus/tests/unit_tests/tools/usage/parsers/test_openai_json_tool_usage_parser.py
import pytest
import json
from autobyteus.tools.usage.parsers import OpenAiJsonToolUsageParser
from autobyteus.llm.utils.response_types import CompleteResponse
from autobyteus.agent.tool_invocation import ToolInvocation

@pytest.fixture
def parser() -> OpenAiJsonToolUsageParser:
    return OpenAiJsonToolUsageParser()

def test_parse_single_valid_tool_call(parser: OpenAiJsonToolUsageParser):
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
    json.dumps({"tool_calls": [{"id": "call_1"}]}),
    "This is text with an invalid json { 'key': 'val' }",
])
def test_no_or_invalid_tool_calls_in_response(parser: OpenAiJsonToolUsageParser, bad_content: str):
    # Arrange
    response = CompleteResponse(content=bad_content)
    # Act
    invocations = parser.parse(response)
    # Assert
    assert len(invocations) == 0
