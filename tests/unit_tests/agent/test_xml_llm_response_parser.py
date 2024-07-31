# File: /home/ryan-ai/miniHDD/Learning/chatgpt/autobyteus/tests/unit_tests/agent/test_xml_llm_response_parser.py

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
    expected_tool_invocation = ToolInvocation(
        name="SearchTool",
        arguments={"query": "encouraging movies for students"}
    )
    
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

def test_parse_complex_xml_structure(parser):
    response = '''
    I have completed my search and found the following information:
    <command name="SendMessageTo">
        <arg name="to_role">CoordinationAgent</arg>
        <arg name="message">
            <list>
                <item>
                    <url>https://github.com/ryan-zheng-teki</url>
                    <summary>GitHub profile of Ryan Zheng, a software engineer with 32 repositories available.</summary>
                </item>
                <item>
                    <url>https://ryan-zheng.medium.com/from-requirements-to-automated-codebase-updates-the-role-of-precise-documentation-ab1bf0c59e3c</url>
                    <summary>Medium article by Ryan Zheng titled "From Requirements to Automated Codebase Updates: The Role of Precise Documentation — AutoByteus Part I."</summary>
                </item>
            </list>
        </arg>
        <arg name="from_role">GoogleSearchAgent</arg>
    </command>
    '''
    
    expected_tool_invocation = ToolInvocation(
        name="SendMessageTo",
        arguments={
            "to_role": "CoordinationAgent",
            "message": '''
            <list>
                <item>
                    <url>https://github.com/ryan-zheng-teki</url>
                    <summary>GitHub profile of Ryan Zheng, a software engineer with 32 repositories available.</summary>
                </item>
                <item>
                    <url>https://ryan-zheng.medium.com/from-requirements-to-automated-codebase-updates-the-role-of-precise-documentation-ab1bf0c59e3c</url>
                    <summary>Medium article by Ryan Zheng titled "From Requirements to Automated Codebase Updates: The Role of Precise Documentation — AutoByteus Part I."</summary>
                </item>
            </list>
        '''.strip(),
            "from_role": "GoogleSearchAgent"
        }
    )
    
    parsed_response = parser.parse_response(response)
    
    assert parsed_response.name == expected_tool_invocation.name
    assert parsed_response.arguments == expected_tool_invocation.arguments

def test_parse_mixed_content_xml(parser):
    response = '''
    <command name="ComplexCommand">
        <arg name="mixed_content">
            This is some text
            <nested>with a nested element</nested>
            and more text
            <another_nested attr="value">
                <deeply_nested>even deeper</deeply_nested>
            </another_nested>
            final text
        </arg>
    </command>
    '''
    
    expected_tool_invocation = ToolInvocation(
        name="ComplexCommand",
        arguments={
            "mixed_content": '''
            This is some text
            <nested>with a nested element</nested>
            and more text
            <another_nested attr="value">
                <deeply_nested>even deeper</deeply_nested>
            </another_nested>
            final text
        '''.strip()
        }
    )
    
    parsed_response = parser.parse_response(response)
    
    assert parsed_response.name == expected_tool_invocation.name
    assert parsed_response.arguments == expected_tool_invocation.arguments