# file: autobyteus/tests/unit_tests/tools/usage/parsers/test_default_xml_tool_usage_parser.py
import pytest
from autobyteus.tools.usage.parsers import DefaultXmlToolUsageParser
from autobyteus.llm.utils.response_types import CompleteResponse
from autobyteus.agent.tool_invocation import ToolInvocation

@pytest.fixture
def parser() -> DefaultXmlToolUsageParser:
    return DefaultXmlToolUsageParser()

@pytest.mark.asyncio
async def test_parse_single_valid_tool_call(parser: DefaultXmlToolUsageParser):
    # Arrange
    response_text = """
    Here is the tool call I'd like to make:
    <tool_calls>
        <tool_call name="search_files" id="call_12345">
            <arguments>
                <arg name="query">customer_report.pdf</arg>
                <arg name="limit">1</arg>
            </arguments>
        </tool_call>
    </tool_calls>
    """
    response = CompleteResponse(content=response_text)

    # Act
    invocations = parser.parse(response)

    # Assert
    assert len(invocations) == 1
    invocation = invocations[0]
    assert isinstance(invocation, ToolInvocation)
    assert invocation.id == "call_12345"
    assert invocation.name == "search_files"
    assert invocation.arguments == {"query": "customer_report.pdf", "limit": "1"}

@pytest.mark.asyncio
async def test_no_tool_calls_block(parser: DefaultXmlToolUsageParser):
    # Arrange
    response = CompleteResponse(content="This is a simple text response with no tools.")
    # Act
    invocations = parser.parse(response)
    # Assert
    assert len(invocations) == 0

@pytest.mark.asyncio
async def test_malformed_xml_is_handled(parser: DefaultXmlToolUsageParser):
    # Arrange
    response = CompleteResponse(content="<tool_calls><tool_call name='bad_xml'><arg name='p1'>v1</tool_call>")
    # Act
    invocations = parser.parse(response)
    # Assert
    assert len(invocations) == 0
