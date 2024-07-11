import pytest
from autobyteus.agent.xml_llm_response_parser import XMLLLMResponseParser
from autobyteus.agent.tool_invocation import ToolInvocation

@pytest.fixture
def parser():
    return XMLLLMResponseParser()

def test_parse_valid_response(parser):
    response = '''
    <command name="SearchTool">
        <arg name="query">python best practices</arg>
    </command>
    '''
    expected_tool_invocation = ToolInvocation(name="SearchTool", arguments={"query": "python best practices"})
    
    parsed_response = parser.parse_response(response)
    
    assert parsed_response.name == expected_tool_invocation.name
    assert parsed_response.arguments == expected_tool_invocation.arguments

def test_parse_invalid_xml(parser):
    response = '''
    <command name="SearchTool">
        <arg name="query>python best practices</arg>
    </command>
    '''
    
    parsed_response = parser.parse_response(response)
    
    assert parsed_response.name is None
    assert parsed_response.arguments is None

def test_parse_non_command_xml(parser):
    response = '''
    <result>
        <item>Python Best Practices</item>
    </result>
    '''
    
    parsed_response = parser.parse_response(response)
    
    assert parsed_response.name is None
    assert parsed_response.arguments is None