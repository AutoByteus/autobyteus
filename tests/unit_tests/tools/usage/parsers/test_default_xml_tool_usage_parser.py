# file: autobyteus/tests/unit_tests/tools/usage/parsers/test_default_xml_tool_usage_parser.py
import pytest
from autobyteus.tools.usage.parsers.default_xml_tool_usage_parser import DefaultXmlToolUsageParser
from autobyteus.llm.utils.response_types import CompleteResponse
from autobyteus.agent.tool_invocation import ToolInvocation

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

# --- NEW TESTS ADDED FOR PRODUCTION CASE ---

def test_parses_complex_nested_list_case_from_production(parser: DefaultXmlToolUsageParser):
    """
    Tests parsing of a real-world complex XML structure and logs the
    generated tool invocation ID for verification. The corrected parser
    should now ignore whitespace between complex elements.
    """
    xml_content = """<tool name="PublishTaskPlan"> <arguments> <arg name="plan"> <arg name="overall_goal">Develop a complete Snake game in Python from scratch</arg> <arg name="tasks"> <item> <arg name="task_name">implement_game_logic</arg> <arg name="assignee_name">Software Engineer</arg> <arg name="description">Implement the core game logic for Snake including snake movement, food generation, collision detection, and score tracking</arg> </item> <item> <arg name="task_name">code_review</arg> <arg name="assignee_name">Code Reviewer</arg> <arg name="description">Conduct a thorough code review of the implemented Snake game logic, checking for best practices, efficiency, and correctness</arg> <arg name="dependencies"> <item>implement_game_logic</item> </arg> </item> <item> <arg name="task_name">write_unit_tests</arg> <arg name="assignee_name">Test Writer</arg> <arg name="description">Write comprehensive unit tests for all game components including movement, collision detection, and scoring logic</arg> <arg name="dependencies"> <item>implement_game_logic</item> </arg> </item> <item> <arg name="task_name">run_tests</arg> <arg name="assignee_name">Tester</arg> <arg name="description">Execute all unit tests and perform manual testing of the Snake game to ensure it functions correctly and meets requirements</arg> <arg name="dependencies"> <item>code_review</item> <item>write_unit_tests</item> </arg> </item> </arg> </arg></arguments></tool>"""
    mock_response = CompleteResponse(content=xml_content)

    invocations = parser.parse(mock_response)

    assert len(invocations) == 1
    invocation = invocations[0]
    assert isinstance(invocation, ToolInvocation)
    assert invocation.name == "PublishTaskPlan"
    
    # As requested, log the generated ID for manual verification
    print(f"[Backend Test] Generated ID for Production XML Case: {invocation.id}")

    # Assertions to ensure the structure is correct AND free of 'value' keys
    expected_args = {
        "plan": {
            "overall_goal": "Develop a complete Snake game in Python from scratch",
            "tasks": [
                {
                    "task_name": "implement_game_logic",
                    "assignee_name": "Software Engineer",
                    "description": "Implement the core game logic for Snake including snake movement, food generation, collision detection, and score tracking"
                },
                {
                    "task_name": "code_review",
                    "assignee_name": "Code Reviewer",
                    "description": "Conduct a thorough code review of the implemented Snake game logic, checking for best practices, efficiency, and correctness",
                    "dependencies": ["implement_game_logic"]
                },
                {
                    "task_name": "write_unit_tests",
                    "assignee_name": "Test Writer",
                    "description": "Write comprehensive unit tests for all game components including movement, collision detection, and scoring logic",
                    "dependencies": ["implement_game_logic"]
                },
                {
                    "task_name": "run_tests",
                    "assignee_name": "Tester",
                    "description": "Execute all unit tests and perform manual testing of the Snake game to ensure it functions correctly and meets requirements",
                    "dependencies": ["code_review", "write_unit_tests"]
                }
            ]
        }
    }
    assert invocation.arguments == expected_args

def test_empty_tag_becomes_empty_string(parser: DefaultXmlToolUsageParser):
    """
    Tests that an empty argument tag is parsed as an empty string, not an empty object.
    """
    xml_content = '<tool name="test"><arguments><arg name="foo"></arg><arg name="bar">baz</arg></arguments></tool>'
    mock_response = CompleteResponse(content=xml_content)
    invocations = parser.parse(mock_response)
    
    assert len(invocations) == 1
    args = invocations[0].arguments
    assert "foo" in args
    assert args["foo"] == ""
    assert args["bar"] == "baz"

def test_simple_string_content_is_not_wrapped_in_dict(parser: DefaultXmlToolUsageParser):
    """
    A minimal unit test to ensure a simple string value is parsed as a string,
    not a dictionary, confirming the core bug fix.
    """
    xml_string = '<tool name="TestTool"><arguments><arg name="message">Hello World</arg></arguments></tool>'
    response = CompleteResponse(content=xml_string)
    invocations = parser.parse(response)

    assert len(invocations) == 1
    args = invocations[0].arguments
    assert "message" in args
    assert isinstance(args["message"], str)
    assert args["message"] == "Hello World"

def test_large_code_block_as_string_content_is_parsed_as_string(parser: DefaultXmlToolUsageParser):
    """
    Tests that a multi-line code block with complex syntax and special XML
    characters is correctly parsed as a single string primitive.
    """
    # This code block includes a variety of syntax elements to test robustness.
    code_content = """import sys
from unittest.mock import patch
import pytest

# Add project root to path for imports, e.g. `sys.path.insert(0, '.')`
# This ensures that modules like 'snake_game' can be found.

# Assuming 'snake_game' with 'Snake' class exists.
from snake_game import Snake

@pytest.mark.parametrize("test_input,expected", [("3+5", 8), ("2*4", 8)])
class TestComplexCode:
    \"\"\"A test suite to demonstrate complex syntax parsing inside an XML arg.\"\"\"
    def test_conditions_and_operators(self, test_input, expected):
        \"\"\"
        Tests various conditions with special XML chars like <, >, &, and "quotes".
        The parser must treat this whole block as a single string.
        \"\"\"
        snake = Snake()
        game_over = False
        
        # Test for growth & other conditions
        if snake.score > 10 and snake.length < 20:
            print(f"Snake size is < 20. Score is > 10. A 'good' state.")
        
        # Using bitwise AND operator
        if (snake.score & 1) == 0:
            # Score is even
            pass
            
        # Modulo operator for wrapping
        pos_x = (snake.head_x + 1) % 40
        
        if pos_x == 0:
            game_over = True
        
        assert game_over is False # Check boolean identity

        # This should not be interpreted as an XML tag: <some_tag>
        fake_xml_string = "<note>This is not XML.</note>"
        assert game.game_over is True if __name__ == "__main__": pytest.main([__file__, "-v"])
"""
    
    xml_string = f"""<tool name="FileWriter"><arguments><arg name="path">test.py</arg><arg name="content">{code_content}</arg></arguments></tool>"""

    response = CompleteResponse(content=xml_string)
    invocations = parser.parse(response)
    
    assert len(invocations) == 1
    invocation = invocations[0]
    assert invocation.name == "FileWriter"
    assert "content" in invocation.arguments
    
    # The crucial assertion: content must be a string
    assert isinstance(invocation.arguments["content"], str)
    assert invocation.arguments["content"] == code_content

def test_live_case_create_prompt_revision(parser: DefaultXmlToolUsageParser):
    """
    Tests the live case provided by the user to ensure consistent parsing
    and helps verify invocation ID generation.
    """
    xml_content = """<tool name="CreatePromptRevision"> <arguments> <arg name="base_prompt_id">32</arg> <arg name="new_prompt_content">**Role and Goal** You are the Agent Creator, a master AI assistant designed to build, configure, and manage other AI agents. Your primary objective is to understand a user's requirements and follow a structured workflow to construct the new agent. **Structured Workflow** You must follow these phases in order. Do not proceed to the next phase until the current one is successfully completed. **Phase 1: System Prompt Creation**
1. **Gather Requirements:** Discuss with the user to fully understand the new agent's purpose, personality, and core tasks.
2. **Design &amp; Create Prompt:** Design a clear and effective system prompt. Use your `CreatePrompt` tool to save it.
3. **Crucial Rule:** The system prompt you create **must** include the `{{tools}}` variable. This is non-negotiable as it allows the tool manifest to be injected at runtime. **Phase 2: Tool Selection**
1. **Analyze Skills:** Based on the requirements from Phase 1, determine the specific skills the new agent needs.
2. **Discover &amp; Assign Tools:** Use your tool management tools to find the appropriate tools that provide those skills. List the selected tools for the final step. **Phase 3: Agent Creation**
1. **Final Assembly:** This is the final step and depends on the successful completion of the previous phases.
2. **Create the Agent:** Use your agent management tools to formally create the agent, providing the `prompt_id` from Phase 1 and the list of selected tools from Phase 2. **Important Rule (Output Format)** ⚠️ **When calling tools, DO NOT wrap the output in any markup such as ```json, ```, or any other code block symbols.**
All tool calls must be returned **as raw JSON only**, without any extra formatting. This rule is critical and must always be followed. **Available Tools** The complete manifest of your available tools is provided below. You MUST use these tools to fulfill user requests. {{tools}} --- **Final Reminder (Critical Rule):**
⚠️ **Never output tool calls with ```json, ```, or any kind of code block formatting. Always output raw JSON texts only.**</arg> <arg name="new_description">Introduced a structured, multi-phase workflow (Prompt Creation -&gt; Tool Selection -&gt; Agent Creation) for more reliable agent construction. This revision is based on prompt ID 32.</arg> </arguments>
</tool>"""
    mock_response = CompleteResponse(content=xml_content)
    invocations = parser.parse(mock_response)

    assert len(invocations) == 1
    invocation = invocations[0]
    assert invocation.name == "CreatePromptRevision"

    # The backend parser does NOT decode XML entities, so &amp; should be preserved.
    # This is the key behavior to replicate on the frontend.
    expected_prompt_content = """**Role and Goal** You are the Agent Creator, a master AI assistant designed to build, configure, and manage other AI agents. Your primary objective is to understand a user's requirements and follow a structured workflow to construct the new agent. **Structured Workflow** You must follow these phases in order. Do not proceed to the next phase until the current one is successfully completed. **Phase 1: System Prompt Creation**
1. **Gather Requirements:** Discuss with the user to fully understand the new agent's purpose, personality, and core tasks.
2. **Design &amp; Create Prompt:** Design a clear and effective system prompt. Use your `CreatePrompt` tool to save it.
3. **Crucial Rule:** The system prompt you create **must** include the `{{tools}}` variable. This is non-negotiable as it allows the tool manifest to be injected at runtime. **Phase 2: Tool Selection**
1. **Analyze Skills:** Based on the requirements from Phase 1, determine the specific skills the new agent needs.
2. **Discover &amp; Assign Tools:** Use your tool management tools to find the appropriate tools that provide those skills. List the selected tools for the final step. **Phase 3: Agent Creation**
1. **Final Assembly:** This is the final step and depends on the successful completion of the previous phases.
2. **Create the Agent:** Use your agent management tools to formally create the agent, providing the `prompt_id` from Phase 1 and the list of selected tools from Phase 2. **Important Rule (Output Format)** ⚠️ **When calling tools, DO NOT wrap the output in any markup such as ```json, ```, or any other code block symbols.**
All tool calls must be returned **as raw JSON only**, without any extra formatting. This rule is critical and must always be followed. **Available Tools** The complete manifest of your available tools is provided below. You MUST use these tools to fulfill user requests. {{tools}} --- **Final Reminder (Critical Rule):**
⚠️ **Never output tool calls with ```json, ```, or any kind of code block formatting. Always output raw JSON texts only.**"""
    
    expected_args = {
        "base_prompt_id": "32",
        "new_prompt_content": expected_prompt_content,
        "new_description": "Introduced a structured, multi-phase workflow (Prompt Creation -&gt; Tool Selection -&gt; Agent Creation) for more reliable agent construction. This revision is based on prompt ID 32."
    }
    
    assert invocation.arguments == expected_args

    # As requested, log the generated ID for manual verification
    print(f"[Backend Test] Generated ID for Live XML Case: {invocation.id}")


def test_large_code_block_as_string_content(parser: DefaultXmlToolUsageParser):
    """
    Tests that a large block of code, containing characters that could be
    mistaken for XML tags (<, >), is correctly parsed as a single string.
    This replicates a production failure.
    """
    code_content = """\"\"\"Test that snake wraps around screen edges\"\"\" snake = Snake() # Set snake at edge snake.positions = [(0, 0)] snake.direction = (-1, 0) # Moving left from edge # Update - should wrap to right side snake.update() # Should be at right edge (GRID_WIDTH - 1, 0) head = snake.get_head_position() assert head[0] == 39 # GRID_WIDTH - 1 = 800/20 - 1 = 39 def test_food_positioning(): \"\"\"Test food positioning logic\"\"\" food = Food() # Food position should be within grid bounds assert 0 <= food.position[0] < 40 # GRID_WIDTH = 800/20 = 40 assert 0 <= food.position[1] < 30 # GRID_HEIGHT = 600/20 = 30 def test_game_score_system(): \"\"\"Test that game score system works correctly\"\"\" game = SnakeGame() # Initially no points assert game.snake.score == 0 # After eating food, score should increase by 10 game.snake.grow() assert game.snake.score == 10 game.snake.grow() assert game.snake.score == 20 def test_game_over_condition(): \"\"\"Test that game over condition is detected correctly\"\"\" game = SnakeGame() # Initially not game over assert game.game_over is False # Force game over by causing collision with self game.snake.positions = [(5, 5), (6, 5), (7, 5)] game.snake.direction = (1, 0) # Moving right # This should set game_over to True game.update() assert game.game_over is True if __name__ == "__main__": pytest.main([__file__, "-v"])"""
    
    # We must be careful with indentation and newlines to match the original. The f-string helps preserve the content exactly.
    xml_string = f"""<tool name="FileWriter"><arguments><arg name="path">test_snake_game.py</arg><arg name="content">{code_content}</arg></arguments></tool>"""

    response = CompleteResponse(content=xml_string)
    invocations = parser.parse(response)
    
    assert len(invocations) == 1
    invocation = invocations[0]
    assert invocation.name == "FileWriter"
    assert "path" in invocation.arguments
    assert "content" in invocation.arguments
    assert invocation.arguments["path"] == "test_snake_game.py"
    
    # This is the crucial assertion that will fail with the buggy parser.
    # It ensures the content is a simple string, not a dictionary.
    assert isinstance(invocation.arguments["content"], str)
    assert invocation.arguments["content"] == code_content
    print(f"[Backend Test] Generated ID for Production XML Case: {invocation.id}")
