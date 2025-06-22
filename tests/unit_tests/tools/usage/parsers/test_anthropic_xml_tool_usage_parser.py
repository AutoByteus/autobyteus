# file: autobyteus/tests/unit_tests/tools/usage/parsers/test_anthropic_xml_tool_usage_parser.py
import pytest
from autobyteus.tools.usage.parsers import AnthropicXmlToolUsageParser
from autobyteus.llm.utils.response_types import CompleteResponse
from autobyteus.agent.tool_invocation import ToolInvocation

@pytest.fixture
def parser() -> AnthropicXmlToolUsageParser:
    return AnthropicXmlToolUsageParser()

@pytest.mark.asyncio
async def test_parse_single_valid_tool_call(parser: AnthropicXmlToolUsageParser):
    # Arrange
    response_text = """
    I think I should use a tool for this. Here is the tool call:
    <tool_calls>
        <tool_call name="get_stock_price" id="tool_123">
            <arguments>
                <arg name="ticker_symbol">GOOG</arg>
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
    assert invocation.id == "tool_123"
    assert invocation.name == "get_stock_price"
    assert invocation.arguments == {"ticker_symbol": "GOOG"}
