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
