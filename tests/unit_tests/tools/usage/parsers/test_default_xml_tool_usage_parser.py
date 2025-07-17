import pytest
from autobyteus.tools.usage.parsers import DefaultXmlToolUsageParser
from autobyteus.llm.utils.response_types import CompleteResponse
from autobyteus.agent.tool_invocation import ToolInvocation
from autobyteus.tools.usage.parsers.exceptions import ToolUsageParseException

@pytest.fixture
def parser() -> DefaultXmlToolUsageParser:
    return DefaultXmlToolUsageParser()

def test_parse_single_tool_not_in_wrapper(parser: DefaultXmlToolUsageParser):
    # Arrange
    response_text = """
    Okay, I will call the tool.
    <tool name="search_files" id="call_xyz">
        <arguments>
            <arg name="query">final_preso.pptx</arg>
        </arguments>
    </tool>
    And that should be it.
    """
    response = CompleteResponse(content=response_text)
    
    # Act
    invocations = parser.parse(response)
    
    # Assert
    assert len(invocations) == 1
    invocation = invocations[0]
    assert invocation.id == "call_xyz"
    assert invocation.name == "search_files"
    assert invocation.arguments == {"query": "final_preso.pptx"}

def test_parse_multiple_separate_tool_blocks(parser: DefaultXmlToolUsageParser):
    # Arrange
    response_text = """
    I will call the first tool.
    <tool name="search_files" id="call_xyz">
        <arguments>
            <arg name="query">final_preso.pptx</arg>
        </arguments>
    </tool>
    Now for the second tool.
    <tool name="send_email" id="call_abc">
        <arguments>
            <arg name="recipient">test@example.com</arg>
        </arguments>
    </tool>
    All done.
    """
    response = CompleteResponse(content=response_text)
    
    # Act
    invocations = parser.parse(response)
    
    # Assert
    assert len(invocations) == 2
    assert invocations[0].id == "call_xyz"
    assert invocations[0].name == "search_files"
    assert invocations[0].arguments == {"query": "final_preso.pptx"}
    assert invocations[1].id == "call_abc"
    assert invocations[1].name == "send_email"
    assert invocations[1].arguments == {"recipient": "test@example.com"}

def test_parse_generates_id_if_missing(parser: DefaultXmlToolUsageParser):
    # Arrange
    response_text = """
    <tool name="get_weather">
        <arguments><arg name="location">london</arg></arguments>
    </tool>
    """
    response = CompleteResponse(content=response_text)

    # Act
    invocations = parser.parse(response)

    # Assert
    assert len(invocations) == 1
    assert invocations[0].id is not None
    assert isinstance(invocations[0].id, str)
    assert len(invocations[0].id) > 10 # Check it's a real ID

def test_no_tool_blocks(parser: DefaultXmlToolUsageParser):
    # Arrange
    response = CompleteResponse(content="This is a simple text response with no tools.")
    # Act
    invocations = parser.parse(response)
    # Assert
    assert len(invocations) == 0

def test_malformed_xml_is_ignored(parser: DefaultXmlToolUsageParser):
    # A malformed block should now be skipped, not raise an exception, allowing other valid tools to be parsed.
    response_text = """
    <tool name='bad_xml'><arg name='p1'>v1</tool>
    <tool name="good_tool"><arguments/></tool>
    """
    response = CompleteResponse(content=response_text)
    # Act
    invocations = parser.parse(response)
    # Assert
    assert len(invocations) == 1
    assert invocations[0].name == "good_tool"

def test_tool_with_no_arguments_tag(parser: DefaultXmlToolUsageParser):
    # Arrange
    response_text = """<tool name="list_buckets"></tool>"""
    response = CompleteResponse(content=response_text)

    # Act
    invocations = parser.parse(response)

    # Assert
    assert len(invocations) == 1
    assert invocations[0].name == "list_buckets"
    assert invocations[0].arguments == {}

def test_tool_with_empty_arguments_tag(parser: DefaultXmlToolUsageParser):
    # Arrange
    response_text = """<tool name="list_buckets"><arguments></arguments></tool>"""
    response = CompleteResponse(content=response_text)

    # Act
    invocations = parser.parse(response)

    # Assert
    assert len(invocations) == 1
    assert invocations[0].name == "list_buckets"
    assert invocations[0].arguments == {}
    
def test_handles_special_chars_in_args(parser: DefaultXmlToolUsageParser):
    # Arrange
    response_text = """
    <tool name="special_chars_test">
        <arguments>
            <arg name="param1">&lt;less-than</arg>
            <arg name="param2">&amp;ampersand</arg>
            <arg name="param3">&quot;quotes&quot;</arg>
        </arguments>
    </tool>
    """
    response = CompleteResponse(content=response_text)
    # Act
    invocations = parser.parse(response)
    # Assert
    assert len(invocations) == 1
    assert invocations[0].arguments == {
        "param1": "<less-than",
        "param2": "&ampersand",
        "param3": '"quotes"'
    }

def test_mixed_valid_and_invalid_blocks_are_handled(parser: DefaultXmlToolUsageParser):
    # An invalid block should be skipped, allowing other valid tools to be parsed.
    response_text = """
    <tool name="valid_tool">
        <arguments><arg name="p1">v1</arg></arguments>
    </tool>
    <tool name="invalid_tool>
        <arguments><arg name="p2">v2</arg>
    </tool>
    """
    response = CompleteResponse(content=response_text)
    invocations = parser.parse(response)
    assert len(invocations) == 1
    assert invocations[0].name == "valid_tool"

@pytest.mark.parametrize("text_fragment", [
    "Here is an incomplete tag <tool name='writer'",
    "What if I just say <tool> in my text?",
    "A self-closing tag <tool/> is not a call.",
    # The parser now skips this because the name is missing.
    "<tool><arguments><arg name='p1'>v1</arg></arguments></tool>",
])
def test_incomplete_or_invalid_tags_are_ignored(parser: DefaultXmlToolUsageParser, text_fragment: str):
    """
    Tests that fragments that look like tool calls but are not valid are ignored
    and do not result in a parsed invocation.
    """
    # Arrange
    response = CompleteResponse(content=text_fragment)
    # Act
    invocations = parser.parse(response)
    # Assert
    assert len(invocations) == 0

def test_realistic_scenario_with_mixed_content(parser: DefaultXmlToolUsageParser):
    # Arrange
    realistic_output = """
    Okay, I understand the request. I need to first read the file, and then write a summary.

    First, I'll read the file content.
    <tool name="read_file">
        <arguments>
            <arg name="path">/user/documents/project_notes.txt</arg>
        </arguments>
    </tool>

    Once I have the content, I will summarize it. I think I should maybe... no, that's not right.
    Let's try to call the write tool. <tool name="write_file"
    Whoops, I made a mistake in that last one. Let's do it correctly.

    <tool name="write_summary_file">
        <arguments>
            <arg name="path">/user/documents/summary.txt</arg>
            <arg name="content">This is the summary.</arg>
        </arguments>
    </tool>

    This should complete the request.
    """
    response = CompleteResponse(content=realistic_output)
    
    # Act
    invocations = parser.parse(response)

    # Assert
    assert len(invocations) == 2
    assert invocations[0].name == "read_file"
    assert invocations[0].arguments == {"path": "/user/documents/project_notes.txt"}
    assert invocations[1].name == "write_summary_file"
    assert "content" in invocations[1].arguments
