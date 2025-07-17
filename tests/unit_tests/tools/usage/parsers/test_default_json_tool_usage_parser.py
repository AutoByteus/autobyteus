# file: autobyteus/tests/unit_tests/tools/usage/parsers/test_default_json_tool_usage_parser.py
import pytest
from autobyteus.tools.usage.parsers import DefaultJsonToolUsageParser
from autobyteus.llm.utils.response_types import CompleteResponse
from autobyteus.agent.tool_invocation import ToolInvocation
from autobyteus.tools.usage.parsers.exceptions import ToolUsageParseException

@pytest.fixture
def parser() -> DefaultJsonToolUsageParser:
    return DefaultJsonToolUsageParser()

@pytest.mark.parametrize("response_text, expected_tool_name, expected_arguments", [
    ('{"tool": {"function": "MyTool", "parameters": {"param1": "value1"}}}', "MyTool", {"param1": "value1"}),
    ('```json\n{"tool": {"function": "CodeTool", "parameters": {"data": [1, 2]}}}\n```', "CodeTool", {"data": [1, 2]}),
    ('Some text... then {"tool": {"function": "TrailingTool", "parameters": {"p": 1}}} and more text', "TrailingTool", {"p": 1}),
    ('{"tool": {"function": "NoParamTool", "parameters": {}}}', "NoParamTool", {}),
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

def test_realistic_scenario_with_mixed_content(parser: DefaultJsonToolUsageParser):
    response_text = """
    Okay, I need to call two tools in my specific format. First, I'll list the tables.
    ```json
    {"tool": {"function": "Tool1", "parameters": {"a": 1}}}
    ```
    I see the tables. Now I need to query one. But first, let me check the OpenAI format, which this parser should ignore:
    {"tool_calls": [{"function": {"name": "IgnoredTool", "arguments": {}}}]}
    Okay, that's not for me. Here is my actual second call:
    {"tool": {"function": "Tool3", "parameters": {"c": 3}}}
    And I'm done.
    """
    response = CompleteResponse(content=response_text)
    invocations = parser.parse(response)
    assert len(invocations) == 2
    assert invocations[0].name == "Tool1"
    assert invocations[0].arguments == {"a": 1}
    assert invocations[1].name == "Tool3"
    assert invocations[1].arguments == {"c": 3}

@pytest.mark.parametrize("response_text", [
    "This is just plain text with no JSON.",
    '{"invalid_json": "MyTool"}', # Not valid json
    "```json\n{'invalid': 'json'}\n```", # Not valid json
    "[]",
    "{}",
    # This parser is strict and should ignore other valid tool formats
    '{"name": "GeminiTool", "args": {}}',
    '{"tool_calls": [{"function": {"name": "OpenAITool"}}]}',
    # Incomplete JSON
    '{"tool": {"function": "IncompleteTool"',
])
def test_invalid_or_non_matching_json(
    parser: DefaultJsonToolUsageParser,
    response_text: str
):
    # Arrange
    response = CompleteResponse(content=response_text)
    # Act
    invocations = parser.parse(response)
    # Assert
    assert len(invocations) == 0

@pytest.mark.parametrize("malformed_text", [
    # Missing function
    '{"tool": {"parameters": {"p": 1}}}',
    # Parameters is not a dict
    '{"tool": {"function": "MyTool", "parameters": "not-a-dict"}}',
    # Tool block is not a dict
    '{"tool": 123}',
])
def test_malformed_tool_structure(parser: DefaultJsonToolUsageParser, malformed_text: str):
    # Arrange
    response = CompleteResponse(content=malformed_text)
    # Act
    invocations = parser.parse(response)
    # Assert
    assert len(invocations) == 0

def test_parameters_is_null_or_missing(parser: DefaultJsonToolUsageParser):
    # Test missing `parameters` key
    response1 = CompleteResponse(content='{"tool": {"function": "MyTool"}}')
    invocations1 = parser.parse(response1)
    assert len(invocations1) == 1
    assert invocations1[0].name == "MyTool"
    assert invocations1[0].arguments == {}
    
    # Test `parameters` is null
    response2 = CompleteResponse(content='{"tool": {"function": "MyTool", "parameters": null}}')
    invocations2 = parser.parse(response2)
    assert len(invocations2) == 1
    assert invocations2[0].name == "MyTool"
    assert invocations2[0].arguments == {}

def test_unexpected_structure_raises_exception(parser: DefaultJsonToolUsageParser):
    # This tests that if the JSON is valid but the structure is wrong in an unhandled way, it raises.
    # For example, if 'parameters' was a list instead of a dict.
    response_text = '{"tool": {"function": "MyTool", "parameters": [1, 2, 3]}}'
    response = CompleteResponse(content=response_text)
    
    # The current parser just logs and continues, resulting in 0 invocations.
    # This is a valid design choice. If it were to raise, the test would be:
    # with pytest.raises(ToolUsageParseException):
    #     parser.parse(response)
    invocations = parser.parse(response)
    assert len(invocations) == 0

def test_parses_multiple_json_objects_from_production_output(parser: DefaultJsonToolUsageParser):
    # This is based on a real production output where two JSON objects were emitted consecutively.
    response_text = """---


{
  "tool": {
    "function": "sqlite_write_query",
    "parameters": {
      "query": "UPDATE Person SET age = 24 WHERE name = 'Normy';"
    }
  }
}
{
  "tool": {
    "function": "sqlite_write_query",
    "parameters": {
      "query": "UPDATE Person SET age = 45 WHERE name = 'Ryan';"
    }
  }
}
---"""
    response = CompleteResponse(content=response_text)

    # Act
    invocations = parser.parse(response)

    # Assert
    assert len(invocations) == 2
    
    # Check first invocation
    assert invocations[0].name == "sqlite_write_query"
    assert invocations[0].arguments == {"query": "UPDATE Person SET age = 24 WHERE name = 'Normy';"}
    
    # Check second invocation
    assert invocations[1].name == "sqlite_write_query"
    assert invocations[1].arguments == {"query": "UPDATE Person SET age = 45 WHERE name = 'Ryan';"}
