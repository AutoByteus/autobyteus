import pytest
import json
from autobyteus.tools.usage.parsers import OpenAiJsonToolUsageParser
from autobyteus.llm.utils.response_types import CompleteResponse
from autobyteus.agent.tool_invocation import ToolInvocation

@pytest.fixture
def parser() -> OpenAiJsonToolUsageParser:
    return OpenAiJsonToolUsageParser()

# --- Tests for the new "Dual Standard" ---

class TestSingleToolStandard:
    def test_parse_valid_single_tool_call(self, parser: OpenAiJsonToolUsageParser):
        # Arrange
        payload = {
            "tool": {
                "function": {
                    "name": "get_weather",
                    "arguments": '{"location": "Boston, MA", "unit": "celsius"}'
                }
            }
        }
        response = CompleteResponse(content=json.dumps(payload))

        # Act
        invocations = parser.parse(response)

        # Assert
        assert len(invocations) == 1
        invocation = invocations[0]
        assert isinstance(invocation, ToolInvocation)
        assert invocation.name == "get_weather"
        assert invocation.arguments == {"location": "Boston, MA", "unit": "celsius"}
        assert invocation.id is not None
        assert invocation.id.startswith("call_")

    @pytest.mark.parametrize("arguments_str", ['{}', ''])
    def test_parse_single_tool_call_with_no_arguments(self, parser: OpenAiJsonToolUsageParser, arguments_str: str):
        # Arrange
        payload = {
            "tool": {
                "function": {
                    "name": "list_files",
                    "arguments": arguments_str
                }
            }
        }
        response = CompleteResponse(content=json.dumps(payload))

        # Act
        invocations = parser.parse(response)

        # Assert
        assert len(invocations) == 1
        invocation = invocations[0]
        assert invocation.name == "list_files"
        assert invocation.arguments == {}

class TestMultipleToolsStandard:
    def test_parse_valid_multiple_tool_calls(self, parser: OpenAiJsonToolUsageParser):
        # Arrange
        payload = {
            "tools": [
                {
                    "function": {
                        "name": "get_weather",
                        "arguments": '{"location": "Boston, MA"}'
                    }
                },
                {
                    "function": {
                        "name": "send_email",
                        "arguments": '{"to": "test@example.com", "subject": "Hello"}'
                    }
                }
            ]
        }
        response = CompleteResponse(content=json.dumps(payload))

        # Act
        invocations = parser.parse(response)

        # Assert
        assert len(invocations) == 2
        assert invocations[0].name == "get_weather"
        assert invocations[0].arguments == {"location": "Boston, MA"}
        assert invocations[1].name == "send_email"
        assert invocations[1].arguments == {"to": "test@example.com", "subject": "Hello"}
    
    def test_parse_empty_tools_list(self, parser: OpenAiJsonToolUsageParser):
        # Arrange
        payload = {"tools": []}
        response = CompleteResponse(content=json.dumps(payload))

        # Act
        invocations = parser.parse(response)

        # Assert
        assert len(invocations) == 0

# --- Negative Tests for Invalid Formats and Malformed Content ---

@pytest.mark.parametrize("invalid_content", [
    # Plain text
    "This is just some text.",
    # Invalid JSON
    "{'tool': 'is not valid json'}",
    # Old format
    json.dumps({"tool_calls": [{"function": {"name": "test"}}]}),
    # Raw list format
    json.dumps([{"function": {"name": "test"}}]),
    # Raw object format
    json.dumps({"function": {"name": "test"}}),
    # Ambiguous format with both keys
    json.dumps({"tool": {}, "tools": []}),
    # Format with neither key
    json.dumps({"other_key": "value"}),
])
def test_parse_invalid_or_unsupported_formats(parser: OpenAiJsonToolUsageParser, invalid_content: str):
    # Arrange
    response = CompleteResponse(content=invalid_content)

    # Act
    invocations = parser.parse(response)

    # Assert
    assert len(invocations) == 0

@pytest.mark.parametrize("malformed_payload", [
    # 'tool' value is not a dictionary
    {"tool": "a string"},
    # 'tools' value is not a list
    {"tools": "a string"},
    # Item in 'tools' list is not a dictionary
    {"tools": ["a string"]},
    # Missing 'function' key
    {"tool": {"name": "test", "arguments": "{}"}},
    # Missing 'name' key in function
    {"tool": {"function": {"arguments": "{}"}}},
    # 'arguments' is not a string
    {"tool": {"function": {"name": "test", "arguments": {"a": "dict"}}}},
    # 'arguments' is an invalid JSON string
    {"tool": {"function": {"name": "test", "arguments": '{"key": "no_closing_brace'}}},
])
def test_parse_malformed_payloads(parser: OpenAiJsonToolUsageParser, malformed_payload: dict):
    # Arrange
    response = CompleteResponse(content=json.dumps(malformed_payload))

    # Act
    invocations = parser.parse(response)

    # Assert
    assert len(invocations) == 0

# --- Test for Helper Functionality ---

def test_parse_json_from_markdown_block(parser: OpenAiJsonToolUsageParser):
    # Arrange
    content = """
Some preceding text.
```json
{
    "tool": {
        "function": {
            "name": "execute_code",
            "arguments": "{\\"code\\": \\"print('hello from markdown')\\"}"
        }
    }
}
```
Some trailing text.
"""
    response = CompleteResponse(content=content)
    
    # Act
    invocations = parser.parse(response)

    # Assert
    assert len(invocations) == 1
    assert invocations[0].name == "execute_code"
    assert invocations[0].arguments == {"code": "print('hello from markdown')"}
