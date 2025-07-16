# file: autobyteus/tests/unit_tests/tools/usage/parsers/test_openai_json_tool_usage_parser.py
import pytest
import json
from autobyteus.tools.usage.parsers import OpenAiJsonToolUsageParser
from autobyteus.llm.utils.response_types import CompleteResponse
from autobyteus.agent.tool_invocation import ToolInvocation
from autobyteus.tools.usage.parsers.exceptions import ToolUsageParseException

@pytest.fixture
def parser() -> OpenAiJsonToolUsageParser:
    return OpenAiJsonToolUsageParser()

# --- Positive tests for various valid formats ---

@pytest.mark.parametrize("payload", [
    # Official format
    {"tool_calls": [{"function": {"name": "get_weather", "arguments": '{"location": "Boston, MA"}'}}]},
    # "tools" key format
    {"tools": [{"function": {"name": "get_weather", "arguments": '{"location": "Boston, MA"}'}}]},
    # "tool" key format
    {"tool": {"function": {"name": "get_weather", "arguments": '{"location": "Boston, MA"}'}}},
    # Raw list format
    [{"function": {"name": "get_weather", "arguments": '{"location": "Boston, MA"}'}}],
    # Raw single object format
    {"function": {"name": "get_weather", "arguments": '{"location": "Boston, MA"}'}},
    # Flattened format (no "function" wrapper)
    {"name": "get_weather", "arguments": {"location": "Boston, MA"}},
])
def test_parse_various_valid_formats(parser: OpenAiJsonToolUsageParser, payload: any):
    response = CompleteResponse(content=json.dumps(payload))
    invocations = parser.parse(response)
    assert len(invocations) == 1
    assert invocations[0].name == "get_weather"
    assert invocations[0].arguments == {"location": "Boston, MA"}

@pytest.mark.parametrize("arguments", [
    '{"location": "Boston, MA"}',  # Stringified JSON
    {"location": "Boston, MA"},    # Native dict
])
def test_parse_different_argument_types(parser: OpenAiJsonToolUsageParser, arguments: any):
    payload = {"tool_calls": [{"function": {"name": "get_weather", "arguments": arguments}}]}
    response = CompleteResponse(content=json.dumps(payload))
    invocations = parser.parse(response)
    assert len(invocations) == 1
    assert invocations[0].arguments == {"location": "Boston, MA"}

@pytest.mark.parametrize("arguments", [
    '{}',      # Empty stringified JSON
    '',        # Empty string
    {},        # Empty dict
    None,      # Null value
])
def test_parse_empty_or_null_arguments(parser: OpenAiJsonToolUsageParser, arguments: any):
    payload = {"tool_calls": [{"function": {"name": "list_files", "arguments": arguments}}]}
    if arguments is None:
        # Also test with the key being completely absent
        del payload["tool_calls"][0]["function"]["arguments"]

    response = CompleteResponse(content=json.dumps(payload))
    invocations = parser.parse(response)
    assert len(invocations) == 1
    assert invocations[0].name == "list_files"
    assert invocations[0].arguments == {}

def test_parse_multiple_tool_calls(parser: OpenAiJsonToolUsageParser):
    payload = {
        "tool_calls": [
            {"function": {"name": "get_weather", "arguments": '{"location": "Boston, MA"}'}},
            {"function": {"name": "send_email", "arguments": {"to": "test@example.com", "subject": "Hello"}}}
        ]
    }
    response = CompleteResponse(content=json.dumps(payload))
    invocations = parser.parse(response)
    assert len(invocations) == 2
    assert invocations[0].name == "get_weather"
    assert invocations[1].name == "send_email"
    assert invocations[1].arguments == {"to": "test@example.com", "subject": "Hello"}

def test_realistic_scenario_with_mixed_content(parser: OpenAiJsonToolUsageParser):
    content = """
I need to run two tools. First, I'll execute some code.
```json
{
    "tool_calls": [{
        "function": {
            "name": "execute_code",
            "arguments": "{\\"code\\": \\"print('hello from markdown')\\"}"
        }
    }]
}
```
Okay, that's done. Now for the second tool, which is a different format.
I'll also add some other JSON that should be ignored.
{"status": "thinking"}
Here is the actual second tool call:
{"name": "another_tool", "arguments": {}}
That's all.
"""
    response = CompleteResponse(content=content)
    invocations = parser.parse(response)
    assert len(invocations) == 2
    assert invocations[0].name == "execute_code"
    assert invocations[0].arguments == {"code": "print('hello from markdown')"}
    assert invocations[1].name == "another_tool"
    assert invocations[1].arguments == {}

# --- Negative Tests for Invalid Formats and Malformed Content ---

@pytest.mark.parametrize("invalid_content", [
    "This is just some text.",
    "{'tool': 'is not valid json'}",
    # Ambiguous format with multiple tool keys is not supported
    json.dumps({"tool": {}, "tools": []}),
    json.dumps({"tool": {}, "tool_calls": []}),
    # Empty lists or objects that are not tool calls
    json.dumps({"tools": []}),
    json.dumps({"other_key": "value"}),
    # Incomplete JSON
    '{"tool_calls": [{"function":',
    '{"name": "unclosed_tool"',
])
def test_parse_invalid_or_non_tool_formats(parser: OpenAiJsonToolUsageParser, invalid_content: str):
    response = CompleteResponse(content=invalid_content)
    invocations = parser.parse(response)
    assert len(invocations) == 0

@pytest.mark.parametrize("malformed_payload", [
    # Item in 'tool_calls' list is not a dictionary
    {"tool_calls": ["a string"]},
    # Missing 'name' key in function
    {"tool_calls": [{"function": {"arguments": "{}"}}]},
    # `arguments` is an invalid type
    {"tool_calls": [{"function": {"name": "test", "arguments": 123}}]},
])
def test_parse_malformed_payloads_are_skipped(parser: OpenAiJsonToolUsageParser, malformed_payload: dict):
    # These are malformed but shouldn't crash the parser, just result in no invocations.
    response = CompleteResponse(content=json.dumps(malformed_payload))
    invocations = parser.parse(response)
    assert len(invocations) == 0

def test_invalid_json_string_for_args_raises_exception(parser: OpenAiJsonToolUsageParser):
    # If `arguments` is a string but not valid JSON, it's a hard error.
    payload = {"tool_calls": [{"function": {"name": "test", "arguments": '{"key": "no_closing_brace'}}]}
    response = CompleteResponse(content=json.dumps(payload))
    with pytest.raises(ToolUsageParseException):
        parser.parse(response)
