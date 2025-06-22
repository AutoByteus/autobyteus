# file: autobyteus/tests/unit_tests/tools/usage/parsers/test_default_json_tool_usage_parser.py
import pytest
from autobyteus.tools.usage.parsers import DefaultJsonToolUsageParser
from autobyteus.llm.utils.response_types import CompleteResponse
from autobyteus.agent.tool_invocation import ToolInvocation

@pytest.fixture
def parser() -> DefaultJsonToolUsageParser:
    return DefaultJsonToolUsageParser()

@pytest.mark.parametrize("response_text, expected_tool_name, expected_arguments", [
    ('{"tool": {"function": "MyTool", "parameters": {"param1": "value1"}}}', "MyTool", {"param1": "value1"}),
    ('```json\n{"tool": {"function": "CodeTool", "parameters": {"data": [1, 2]}}}\n```', "CodeTool", {"data": [1, 2]}),
    ('Some text... then {"tool": {"function": "TrailingTool", "parameters": {"p": 1}}}', "TrailingTool", {"p": 1}),
    ('{"tool": {"function": "NoParamTool", "parameters": {}}}', "NoParamTool", {}),
    ('{"tool": {"function": "NullParamTool", "parameters": null}}', "NullParamTool", {}),
])
def test_valid_single_tool_call_variants(
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

def test_multiple_tool_calls_in_list(parser: DefaultJsonToolUsageParser):
    response_text = """
    [
        {"tool": {"function": "Tool1", "parameters": {"a": 1}}},
        {"tool": {"function": "Tool2", "parameters": {"b": 2}}}
    ]
    """
    response = CompleteResponse(content=response_text)
    invocations = parser.parse(response)
    assert len(invocations) == 2
    assert invocations[0].name == "Tool1"
    assert invocations[0].arguments == {"a": 1}
    assert invocations[1].name == "Tool2"
    assert invocations[1].arguments == {"b": 2}

def test_multiple_tool_calls_in_tools_key(parser: DefaultJsonToolUsageParser):
    response_text = """
    {
        "thought": "I need to call two tools.",
        "tools": [
            {"tool": {"function": "ToolA", "parameters": {"x": "y"}}},
            {"tool": {"function": "ToolB", "parameters": {"z": "w"}}}
        ]
    }
    """
    response = CompleteResponse(content=response_text)
    invocations = parser.parse(response)
    assert len(invocations) == 2
    assert invocations[0].name == "ToolA"
    assert invocations[1].name == "ToolB"

@pytest.mark.parametrize("response_text", [
    "This is just plain text with no JSON.",
    "{'invalid_json': 'MyTool'}",
    "```json\n{'invalid': 'json'}\n```",
    "{\"tool\": {\"parameters\": {\"p\": 1}}}", # missing function
    "{\"tool\": {\"function\": \"MyTool\"}}", # missing parameters, should parse as empty dict.
    "{\"tool\": 123}", # invalid tool block
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
    # The case with missing parameters should still be parsed, so we check for that.
    if '"function": "MyTool"' in response_text and '"parameters"' not in response_text:
        assert len(invocations) == 1
        assert invocations[0].name == "MyTool"
        assert invocations[0].arguments == {}
    else:
        assert len(invocations) == 0
