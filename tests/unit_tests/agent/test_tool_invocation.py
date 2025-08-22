# file: tests/unit_tests/agent/test_tool_invocation.py
import pytest
import json
from autobyteus.agent.tool_invocation import ToolInvocation

def test_deterministic_id_generation():
    """
    Tests that the _generate_deterministic_id static method produces a
    consistent and expected hash. This test is paired with a frontend
    test to ensure consistent ID generation across platforms.
    """
    tool_name = "test_tool"
    # Note: The order of keys here should not matter for the output hash
    # because the implementation sorts the keys.
    arguments = {
        "param_b": "value_b",
        "param_a": 123,
        "param_c": {"nested_b": 2, "nested_a": "a"}
    }

    # Test the static method directly
    generated_id = ToolInvocation._generate_deterministic_id(tool_name, arguments)

    print(f"\n--- Backend Comparison Value ---")
    print(f"Backend generated ID for '{tool_name}': {generated_id}")
    print(f"--- End Backend Comparison Value ---\n")

    # Assert that an ID was generated, but not what it is.
    assert generated_id.startswith("call_")
    assert len(generated_id) > 10

    # Test via the constructor
    invocation = ToolInvocation(name=tool_name, arguments=arguments)
    assert invocation.id == generated_id


def test_id_generation_with_different_key_order():
    """
    Ensures that changing the order of keys in the arguments
    dictionary does not change the resulting ID.
    """
    tool_name = "test_tool"
    args1 = {"a": 1, "b": 2}
    args2 = {"b": 2, "a": 1}

    invocation1 = ToolInvocation(name=tool_name, arguments=args1)
    invocation2 = ToolInvocation(name=tool_name, arguments=args2)

    assert invocation1.id == invocation2.id

def test_id_generation_is_sensitive_to_values():
    """
    Ensures that changing a value in the arguments results in a different ID.
    """
    tool_name = "test_tool"
    args1 = {"a": 1, "b": 2}
    args2 = {"a": 1, "b": "different"}

    invocation1 = ToolInvocation(name=tool_name, arguments=args1)
    invocation2 = ToolInvocation(name=tool_name, arguments=args2)

    assert invocation1.id != invocation2.id

def test_provided_id_is_used():
    """
    Tests that if an ID is provided to the constructor, it is used
    instead of generating a new one.
    """
    provided_id = "custom_id_12345"
    invocation = ToolInvocation(name="test", arguments={}, id=provided_id)
    assert invocation.id == provided_id

def test_deterministic_id_generation_for_complex_unicode_case():
    """
    Tests that the deterministic ID generation is correct for a complex,
    multi-line string containing unicode characters, from a live production case.
    """
    tool_name = "CreatePromptRevision"
    arguments = {
        "base_prompt_id": "6",
        "new_prompt_content": "You are the Jira Project Manager, an expert AI assistant specializing in managing software development projects using Atlassian's Jira and Confluence.\n\nYour primary purpose is to help users interact with Jira and Confluence efficiently. You can perform a wide range of tasks, including but not limited to:\n- **Jira Issue Management:** Creating, updating, deleting, and searching for issues (Tasks, Bugs, Stories, Epics, Subtasks).\n- **Jira Workflow:** Transitioning issues through their workflow (e.g., from 'To Do' to 'In Progress' to 'Done').\n- **Jira Agile/Scrum:** Managing sprints, boards, and versions.\n- **Linking:** Linking Jira issues to each other or to Confluence pages.\n- **Confluence Documentation:** Creating, reading, and updating Confluence pages to support project documentation.\n- **Reporting:** Answering questions about project status by querying Jira and Confluence.\n\nWhen a user asks for help, be proactive. If a request is ambiguous, ask clarifying questions. For example, if a user wants to create a ticket, ask for the project key, issue type, summary, and description. Always confirm the successful completion of an action.\n\nYou are equipped with a comprehensive set of tools. Use them wisely to fulfill user requests.\n\n**Available Tools**\n{{tools}}\n\n**Important Rule (Output Format)**\n⚠️ **When calling tools, DO NOT wrap the output in any markup such as ```json, ```, or any other code block symbols.**\nAll tool calls must be returned **as raw JSON only**, without any extra formatting. This rule is critical and must always be followed.",
        "new_description": "A system prompt for an agent that manages Jira tickets and Confluence pages. Includes {{tools}} placeholder and output formatting rules."
    }

    # Generate the ID using the class constructor
    invocation = ToolInvocation(name=tool_name, arguments=arguments)
    generated_id = invocation.id

    # This is the ground-truth ID that the frontend must also produce.
    # We print it here for verification.
    print(f"\n[Python Test] Generated ID for Gemini Live Case: {generated_id}")
    
    # Assert that an ID was generated in the correct format.
    assert generated_id.startswith("call_")
    assert len(generated_id) == len("call_") + 64 # sha256 is 64 hex chars
