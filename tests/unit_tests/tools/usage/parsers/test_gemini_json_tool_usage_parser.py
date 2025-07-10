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

@pytest.mark.parametrize("bad_response", [
    "Just some text, no JSON.",
    '```json\n{"name": "tool_one"}\n```', # Missing 'args'
    '```json\n{"args": {"p": 1}}\n```', # Missing 'name'
    '```json\n{"name": "bad_args", "args": "not a dict"}\n```', # 'args' is not a dict
    # Test that a list of tool calls is now ignored, as the parser only handles single objects
    '''
    ```json
    [
        {"name": "get_file_content", "args": {"path": "/path/to/file.txt"}},
        {"name": "analyze_sentiment", "args": {"text": "This is great!"}}
    ]
    ```
    ''',
    # Test that a raw list is ignored by the extractor
    '[{"name": "get_file_content", "args": {"path": "/path/to/file.txt"}}]'
])
def test_malformed_or_invalid_tool_calls(parser: GeminiJsonToolUsageParser, bad_response: str):
    # Arrange
    response = CompleteResponse(content=bad_response)
    
    # Act
    invocations = parser.parse(response)

    # Assert
    assert len(invocations) == 0
