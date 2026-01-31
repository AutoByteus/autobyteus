# file: tests/unit_tests/agent/test_tool_invocation.py
import pytest
from autobyteus.agent.tool_invocation import ToolInvocation

def test_id_must_be_non_empty():
    with pytest.raises(ValueError, match="requires a non-empty id"):
        ToolInvocation(name="test_tool", arguments={}, id="")

def test_provided_id_is_used():
    """
    Tests that if an ID is provided to the constructor, it is used
    instead of generating a new one.
    """
    provided_id = "custom_id_12345"
    invocation = ToolInvocation(name="test", arguments={}, id=provided_id)
    assert invocation.id == provided_id

def test_turn_id_is_optional_and_stored():
    invocation = ToolInvocation(name="test", arguments={}, id="inv_1", turn_id="turn_0001")
    assert invocation.turn_id == "turn_0001"
