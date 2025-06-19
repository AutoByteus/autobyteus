# file: autobyteus/tests/unit_tests/tools/usage/parsers/test_default_xml_tool_usage_parser.py
import pytest
from autobyteus.tools.usage.parsers import DefaultXmlToolUsageParser
from autobyteus.llm.utils.response_types import CompleteResponse
from autobyteus.agent.tool_invocation import ToolInvocation

@pytest.fixture
def parser() -> DefaultXmlToolUsageParser:
    return DefaultXmlToolUsageParser()

def test_parse_multiple_tools_in_wrapper(parser: DefaultXmlToolUsageParser):
    # Arrange
    response_text = """
    Here are the tool calls I'd like to make:
    <tools>
        <tool name="search_files" id="call_123">
            <arguments>
                <arg name="query">customer_report.pdf</arg>
            </arguments>
        </tool>
        <tool name="send_email" id="call_456">
            <arguments>
                <arg name="recipient">test@example.com</arg>
                <arg name="subject">Report Found</arg>
            </arguments>
        </tool>
    </tools>
    """
    response = CompleteResponse(content=response_text)

    # Act
    invocations = parser.parse(response)

    # Assert
    assert len(invocations) == 2
    assert invocations[0].id == "call_123"
    assert invocations[0].name == "search_files"
    assert invocations[0].arguments == {"query": "customer_report.pdf"}
    assert invocations[1].id == "call_456"
    assert invocations[1].name == "send_email"
    assert invocations[1].arguments == {"recipient": "test@example.com", "subject": "Report Found"}

def test_parse_single_tool_not_in_wrapper(parser: DefaultXmlToolUsageParser):
    # Arrange
    response_text = """
    Okay, I will call the tool.
    <tool name="search_files" id="call_xyz">
        <arguments>
            <arg name="query">final_preso.pptx</arg>
        </arguments>
    </tool>
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

def test_malformed_xml_is_handled(parser: DefaultXmlToolUsageParser):
    # Arrange
    response = CompleteResponse(content="<tools><tool name='bad_xml'><arg name='p1'>v1</tool>")
    # Act
    invocations = parser.parse(response)
    # Assert
    assert len(invocations) == 0

def test_tool_with_no_arguments_is_parsed_correctly(parser: DefaultXmlToolUsageParser):
    # Arrange
    response_text = """<tool name="list_buckets"></tool>"""
    response = CompleteResponse(content=response_text)

    # Act
    invocations = parser.parse(response)

    # Assert
    assert len(invocations) == 1
    assert invocations[0].name == "list_buckets"
    assert invocations[0].arguments == {}
