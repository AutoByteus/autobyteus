# file: autobyteus/tests/unit_tests/tools/usage/parsers/test_default_json_tool_usage_parser.py
import pytest
from autobyteus.tools.usage.parsers import DefaultJsonToolUsageParser
from autobyteus.llm.utils.response_types import CompleteResponse
from autobyteus.agent.tool_invocation import ToolInvocation

@pytest.fixture
def parser() -> DefaultJsonToolUsageParser:
    return DefaultJsonToolUsageParser()

@pytest.mark.parametrize("response_text, expected_tool_name, expected_arguments", [
    ('{"name": "MyTool", "arguments": {"param1": "value1"}}', "MyTool", {"param1": "value1"}),
    ('{"tool_calls": [{"id": "call_123", "type": "function", "function": {"name": "OpenAITool", "arguments": "{\\"key\\": \\"val\\"}"}}]}', "OpenAITool", {"key": "val"}),
    ('{"name": "GeminiTool", "args": {"query": "test"}}', "GeminiTool", {"query": "test"}),
    ('```json\n{"name": "CodeTool", "arguments": {"data": [1, 2]}}\n```', "CodeTool", {"data": [1, 2]}),
    ('[{"name": "ListTool", "arguments": {"item": "A"}}]', "ListTool", {"item": "A"}),
    ('Some thinking... and then the action: {"name": "TrailingTool", "arguments": {"p": 1}}', "TrailingTool", {"p": 1}),
])
def test_valid_json_variants_are_parsed(
    parser: DefaultJsonToolUsageParser,
    response_text: str,
    expected_tool_name: str,
    expected_arguments: dict
):
    # Arrange
    response = CompleteResponse(content=response_text)

    # Act
    invocations = parser.parse(response)

    # Assert
    assert len(invocations) == 1
    invocation = invocations[0]
    assert isinstance(invocation, ToolInvocation)
    assert invocation.name == expected_tool_name
    assert invocation.arguments == expected_arguments

@pytest.mark.parametrize("response_text", [
    "This is just plain text with no JSON.",
    "{'tool_name': 'MyTool'}",
    "```json\n{'invalid': 'json'}\n```",
    "{\"name\": \"MissingArgs\"}",
    "{\"arguments\": {\"param\": 1}}",
    "[]",
    "[{\"not_a_tool_call\": true}]",
    "{}",
])
def test_invalid_or_non_tool_json(
    parser: DefaultJsonToolUsageParser,
    response_text: str
):
    # Arrange
    response = CompleteResponse(content=response_text)

    # Act
    invocations = parser.parse(response)

    # Assert
    assert len(invocations) == 0
