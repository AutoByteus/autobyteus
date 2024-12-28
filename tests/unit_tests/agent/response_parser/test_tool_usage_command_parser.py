
import pytest
from autobyteus.agent.response_parser.tool_usage_command_parser import ToolUsageCommandParser
from autobyteus.agent.tool_invocation import ToolInvocation

@pytest.fixture
def parser():
    return ToolUsageCommandParser()

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

def test_parse_web_element_trigger_command(parser):
    response = '''
    <command name="SendMessageTo">
        <arg name="recipient_role_name">CoordinationAgent</arg>
        <arg name="recipient_agent_id">CoordinationAgent-001</arg>
        <arg name="content">
            **Summary of the Product Details:**
            [Content omitted for brevity]
        </arg>
        <arg name="message_type">TASK_RESULT</arg>
        <arg name="sender_agent_id">page_reader_agent-001</arg>
    </command>
    '''
    expected_tool_invocation = ToolInvocation(
        name="SendMessageTo",
        arguments={
            "recipient_role_name": "CoordinationAgent",
            "recipient_agent_id": "CoordinationAgent-001",
            "content": "**Summary of the Product Details:**\n[Content omitted for brevity]",
            "message_type": "TASK_RESULT",
            "sender_agent_id": "page_reader_agent-001"
        }
    )
    
    parsed_response = parser.parse_response(response)
    
    assert parsed_response.name == expected_tool_invocation.name
    assert parsed_response.arguments == expected_tool_invocation.arguments

def test_parse_special_characters_response(parser):
    response = '''
    <command name="SendMessageTo">
        <arg name="recipient_role_name">CoordinationAgent</arg>
        <arg name="recipient_agent_id">CoordinationAgent-001</arg>
        <arg name="content">Here are the most relevant URLs with brief summaries...</arg>
        <arg name="message_type">TASK_RESULT</arg>
        <arg name="sender_agent_id">GoogleSearchAgent-001</arg>
    </command>
    '''
    expected_tool_invocation = ToolInvocation(
        name="SendMessageTo",
        arguments={
            "recipient_role_name": "CoordinationAgent",
            "recipient_agent_id": "CoordinationAgent-001",
            "content": "Here are the most relevant URLs with brief summaries...",
            "message_type": "TASK_RESULT",
            "sender_agent_id": "GoogleSearchAgent-001"
        }
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
    <command name="SearchTool>
        <arg name="query">encouraging movies for students</arg>
    </command>
    '''
    
    parsed_response = parser.parse_response(response)
    
    assert parsed_response.name is None
    assert parsed_response.arguments is None

def test_parse_complex_xml_structure(parser):
    response = '''
    <command name="SendMessageTo">
        <arg name="to_role">CoordinationAgent</arg>
        <arg name="message">
            <list>
                <item>
                    <url>https://github.com/ryan-zheng-teki</url>
                    <summary>GitHub profile of Ryan Zheng</summary>
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
            "message": '''<list>
                <item>
                    <url>https://github.com/ryan-zheng-teki</url>
                    <summary>GitHub profile of Ryan Zheng</summary>
                </item>
            </list>'''.strip(),
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
        </arg>
    </command>
    '''
    
    expected_tool_invocation = ToolInvocation(
        name="ComplexCommand",
        arguments={
            "mixed_content": '''This is some text
            <nested>with a nested element</nested>
            and more text'''.strip()
        }
    )
    
    parsed_response = parser.parse_response(response)
    
    assert parsed_response.name == expected_tool_invocation.name
    assert parsed_response.arguments == expected_tool_invocation.arguments
