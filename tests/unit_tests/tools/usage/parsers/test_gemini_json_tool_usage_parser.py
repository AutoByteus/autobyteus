# file: autobyteus/tests/unit_tests/tools/usage/parsers/test_gemini_json_tool_usage_parser.py
import pytest
from autobyteus.tools.usage.parsers import GeminiJsonToolUsageParser
from autobyteus.llm.utils.response_types import CompleteResponse
from autobyteus.agent.tool_invocation import ToolInvocation

@pytest.fixture
def parser() -> GeminiJsonToolUsageParser:
    return GeminiJsonToolUsageParser()

def test_parse_single_valid_tool_call_in_markdown(parser: GeminiJsonToolUsageParser):
    # Arrange
    response_text = 'Okay, I will search for that.\n```json\n{"name": "search_web", "args": {"query": "latest AI news"}}\n```'
    response = CompleteResponse(content=response_text)

    # Act
    invocations = parser.parse(response)

    # Assert
    assert len(invocations) == 1
    invocation = invocations[0]
    assert isinstance(invocation, ToolInvocation)
    assert invocation.name == "search_web"
    assert invocation.arguments == {"query": "latest AI news"}

def test_parse_single_valid_tool_call_no_markdown(parser: GeminiJsonToolUsageParser):
    # Arrange
    response_text = '{"name": "search_web", "args": {"query": "latest AI news"}}'
    response = CompleteResponse(content=response_text)

    # Act
    invocations = parser.parse(response)

    # Assert
    assert len(invocations) == 1
    invocation = invocations[0]
    assert isinstance(invocation, ToolInvocation)
    assert invocation.name == "search_web"
    assert invocation.arguments == {"query": "latest AI news"}

def test_realistic_scenario_with_mixed_content(parser: GeminiJsonToolUsageParser):
    response_text = """
    Thinking... I should use a tool for this.
    First tool: {"name": "Tool1", "args": {"a": 1}}.
    Now, let's consider this other JSON which is not a tool call for me: {"tool": {"function": "Ignored"}}
    And finally, the second tool I need to call.
    {"name": "Tool3", "args": {"c": 3}}
    ```
    All done.
    """
    response = CompleteResponse(content=response_text)
    invocations = parser.parse(response)
    assert len(invocations) == 2
    assert invocations[0].name == "Tool1"
    assert invocations[0].arguments == {"a": 1}
    assert invocations[1].name == "Tool3"
    assert invocations[1].arguments == {"c": 3}


@pytest.mark.parametrize("bad_response", [
    "Just some text, no JSON.",
    '```json\n{"name": "tool_one"}\n```', # Missing 'args'
    '```json\n{"args": {"p": 1}}\n```', # Missing 'name'
    '```json\n{"name": "bad_args", "args": "not a dict"}\n```', # 'args' is not a dict
    '```json\n{"name": "bad_args_list", "args": []}\n```', # 'args' is a list, not a dict
    # Test that other valid tool formats are ignored
    '{"tool": {"function": "SomeTool", "parameters": {}}}',
    '[{"name": "get_file_content", "args": {"path": "/path/to/file.txt"}}]', # Raw list is ignored
    # Incomplete JSON
    '{"name": "search_web", "args": {"query": "latest AI news"',
])
def test_malformed_or_invalid_tool_calls(parser: GeminiJsonToolUsageParser, bad_response: str):
    # Arrange
    response = CompleteResponse(content=bad_response)
    
    # Act
    invocations = parser.parse(response)

    # Assert
    assert len(invocations) == 0
