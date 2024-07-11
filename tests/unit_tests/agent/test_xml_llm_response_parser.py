import pytest
from autobyteus.agent.xml_llm_response_parser import XMLLLMResponseParser
from autobyteus.agent.tool_invocation import ToolInvocation

@pytest.fixture
def parser():
    return XMLLLMResponseParser()

def test_parse_valid_response(parser):
    response = '''
    I am currently in my reasoning phase, strategizing the best course of action to complete this task.
    To recommend an encouraging movie for students, I should first find out what movies are popular in this category.
    <command name="SearchTool">
        <arg name="query">encouraging movies for students</arg>
    </command>
    I will stop here now and wait for the SearchTool to return the results...
    '''
    expected_tool_invocation = ToolInvocation(name="SearchTool", arguments={"query": "encouraging movies for students"})
    
    parsed_response = parser.parse_response(response)
    
    assert parsed_response.name == expected_tool_invocation.name
    assert parsed_response.arguments == expected_tool_invocation.arguments

def test_parse_response_without_command(parser):
    response = '''
    I am currently in my reasoning phase, strategizing the best course of action to complete this task.
    To recommend an encouraging movie for students, I should first find out what movies are popular in this category.
    I will stop here now and wait for the SearchTool to return the results...
    '''
    
    parsed_response = parser.parse_response(response)
    
    assert parsed_response.name is None
    assert parsed_response.arguments is None

def test_parse_invalid_xml(parser):
    response = '''
    I am currently in my reasoning phase, strategizing the best course of action to complete this task.
    To recommend an encouraging movie for students, I should first find out what movies are popular in this category.
    <command name="SearchTool>
        <arg name="query">encouraging movies for students</arg>
    </command>
    I will stop here now and wait for the SearchTool to return the results...
    '''
    
    parsed_response = parser.parse_response(response)
    
    assert parsed_response.name is None
    assert parsed_response.arguments is None