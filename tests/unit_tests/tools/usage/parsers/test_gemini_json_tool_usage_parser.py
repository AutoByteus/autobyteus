# file: autobyteus/tests/unit_tests/tools/usage/parsers/test_gemini_json_tool_usage_parser.py
import pytest
from autobyteus.tools.usage.parsers import GeminiJsonToolUsageParser
from autobyteus.llm.utils.response_types import CompleteResponse
from autobyteus.agent.tool_invocation import ToolInvocation

@pytest.fixture
def parser() -> GeminiJsonToolUsageParser:
    return GeminiJsonToolUsageParser()

def test_parse_single_valid_tool_call(parser: GeminiJsonToolUsageParser):
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

def test_parse_multiple_tool_calls_in_list(parser: GeminiJsonToolUsageParser):
    # Arrange
    response_text = '''
    ```json
    [
        {"name": "get_file_content", "args": {"path": "/path/to/file.txt"}},
        {"name": "analyze_sentiment", "args": {"text": "This is great!"}}
    ]
    ```
    '''
    response = CompleteResponse(content=response_text)

    # Act
    invocations = parser.parse(response)

    # Assert
    assert len(invocations) == 2
    assert invocations[0].name == "get_file_content"
    assert invocations[1].name == "analyze_sentiment"

@pytest.mark.parametrize("bad_response", [
    "Just some text, no JSON.",
    '```json\n{"name": "tool_one"}\n```',
    '```json\n{"args": {"p": 1}}\n```',
    '```json\n{"name": "bad_args", "args": "not a dict"}\n```',
])
def test_malformed_or_incomplete_tool_calls(parser: GeminiJsonToolUsageParser, bad_response: str):
    # Arrange
    response = CompleteResponse(content=bad_response)
    
    # Act
    invocations = parser.parse(response)

    # Assert
    assert len(invocations) == 0
