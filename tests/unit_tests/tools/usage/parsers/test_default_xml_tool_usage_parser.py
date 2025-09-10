# file: autobyteus/tests/unit_tests/tools/usage/parsers/test_default_xml_tool_usage_parser.py
import pytest
from autobyteus.tools.usage.parsers.default_xml_tool_usage_parser import DefaultXmlToolUsageParser
from autobyteus.llm.utils.response_types import CompleteResponse

@pytest.fixture
def parser():
    return DefaultXmlToolUsageParser()

def test_parse_simple_tool_call(parser: DefaultXmlToolUsageParser):
    xml_string = """
    <tool name="SimpleTool">
        <arguments>
            <arg name="param1">value1</arg>
        </arguments>
    </tool>
    """
    response = CompleteResponse(content=xml_string)
    invocations = parser.parse(response)
    
    assert len(invocations) == 1
    assert invocations[0].name == "SimpleTool"
    assert invocations[0].arguments == {"param1": "value1"}

def test_parse_nested_object(parser: DefaultXmlToolUsageParser):
    xml_string = """
    <tool name="NestedTool">
        <arguments>
            <arg name="config">
                <arg name="setting">true</arg>
                <arg name="level">5</arg>
            </arg>
        </arguments>
    </tool>
    """
    response = CompleteResponse(content=xml_string)
    invocations = parser.parse(response)
    
    assert len(invocations) == 1
    assert invocations[0].name == "NestedTool"
    assert invocations[0].arguments == {"config": {"setting": "true", "level": "5"}}

def test_parse_list_with_item_tags(parser: DefaultXmlToolUsageParser):
    xml_string = """
    <tool name="ListTool">
        <arguments>
            <arg name="items">
                <item>apple</item>
                <item>banana</item>
            </arg>
        </arguments>
    </tool>
    """
    response = CompleteResponse(content=xml_string)
    invocations = parser.parse(response)
    
    assert len(invocations) == 1
    assert invocations[0].name == "ListTool"
    assert invocations[0].arguments == {"items": ["apple", "banana"]}

def test_parse_list_of_objects(parser: DefaultXmlToolUsageParser):
    xml_string = """
    <tool name="ListOfObjectsTool">
        <arguments>
            <arg name="tasks">
                <item>
                    <arg name="task_name">implement_logic</arg>
                    <arg name="status">done</arg>
                </item>
                 <item>
                    <arg name="task_name">write_docs</arg>
                    <arg name="status">pending</arg>
                </item>
            </arg>
        </arguments>
    </tool>
    """
    response = CompleteResponse(content=xml_string)
    invocations = parser.parse(response)
    
    assert len(invocations) == 1
    assert invocations[0].name == "ListOfObjectsTool"
    
    tasks = invocations[0].arguments["tasks"]
    assert isinstance(tasks, list)
    assert len(tasks) == 2
    assert tasks[0] == {"task_name": "implement_logic", "status": "done"}
    assert tasks[1] == {"task_name": "write_docs", "status": "pending"}

def test_stricter_parser_treats_stringified_json_as_string(parser: DefaultXmlToolUsageParser):
    """
    Tests that the stricter parser no longer interprets JSON-like strings.
    It should treat the content as a literal string.
    """
    xml_string = '<tool name="BadListTool"><arguments><arg name="deps">["task1", "task2"]</arg></arguments></tool>'
    response = CompleteResponse(content=xml_string)
    invocations = parser.parse(response)
    
    assert len(invocations) == 1
    assert invocations[0].name == "BadListTool"
    # The value should be the literal string, not a list
    assert invocations[0].arguments == {"deps": '["task1", "task2"]'}

def test_stricter_parser_treats_malformed_list_as_string(parser: DefaultXmlToolUsageParser):
    """
    Tests that the stricter parser treats malformed, unquoted list-like strings
    as a single literal string.
    """
    xml_string = '<tool name="BadListTool"><arguments><arg name="deps">[task1, task2]</arg></arguments></tool>'
    response = CompleteResponse(content=xml_string)
    invocations = parser.parse(response)
    
    assert len(invocations) == 1
    assert invocations[0].name == "BadListTool"
    # The value should be the literal string, not a list
    assert invocations[0].arguments == {"deps": "[task1, task2]"}

def test_parse_string_that_looks_like_json(parser: DefaultXmlToolUsageParser):
    """
    Tests that a string containing brackets is treated as a plain string.
    This behavior is unchanged.
    """
    xml_string = """
    <tool name="NoteTool">
        <arguments>
            <arg name="note">[This is a note, not JSON]</arg>
        </arguments>
    </tool>
    """
    response = CompleteResponse(content=xml_string)
    invocations = parser.parse(response)
    
    assert len(invocations) == 1
    assert invocations[0].arguments == {"note": "[This is a note, not JSON]"}

def test_parse_arg_with_unescaped_xml_chars_in_content(parser: DefaultXmlToolUsageParser):
    """
    Tests that the parser can handle an <arg> tag containing raw code with
    special XML characters like '<' and '>', which should be escaped by the pre-processor.
    """
    code_content = "if x < 5 and y > 10:\n    print('&& success!')"
    xml_string = f"""
    <tool name="CodeRunner">
        <arguments>
            <arg name="code">{code_content}</arg>
        </arguments>
    </tool>
    """
    response = CompleteResponse(content=xml_string)
    invocations = parser.parse(response)
    
    assert len(invocations) == 1
    invocation = invocations[0]
    assert invocation.name == "CodeRunner"
    # The content should be preserved exactly as the original string
    assert invocation.arguments == {"code": code_content}
