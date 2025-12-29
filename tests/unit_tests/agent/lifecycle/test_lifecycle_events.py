# file: tests/unit_tests/agent/lifecycle/test_lifecycle_events.py
"""
Tests for LifecycleEvent enum.
"""
import pytest
from autobyteus.agent.lifecycle.events import LifecycleEvent


class TestLifecycleEvent:
    """Tests for the LifecycleEvent enum."""

    def test_all_lifecycle_events_exist(self):
        """Verify all expected lifecycle events are defined."""
        expected_events = [
            "AGENT_READY",
            "BEFORE_LLM_CALL",
            "AFTER_LLM_RESPONSE",
            "BEFORE_TOOL_EXECUTE",
            "AFTER_TOOL_EXECUTE",
            "AGENT_SHUTTING_DOWN",
        ]
        actual_events = [e.name for e in LifecycleEvent]
        assert set(actual_events) == set(expected_events)

    def test_lifecycle_event_values(self):
        """Verify event values are lowercase snake_case strings."""
        assert LifecycleEvent.AGENT_READY.value == "agent_ready"
        assert LifecycleEvent.BEFORE_LLM_CALL.value == "before_llm_call"
        assert LifecycleEvent.AFTER_LLM_RESPONSE.value == "after_llm_response"
        assert LifecycleEvent.BEFORE_TOOL_EXECUTE.value == "before_tool_execute"
        assert LifecycleEvent.AFTER_TOOL_EXECUTE.value == "after_tool_execute"
        assert LifecycleEvent.AGENT_SHUTTING_DOWN.value == "agent_shutting_down"

    def test_lifecycle_event_is_string_enum(self):
        """Verify LifecycleEvent inherits from str for easy string operations."""
        assert isinstance(LifecycleEvent.AGENT_READY, str)
        assert LifecycleEvent.AGENT_READY == "agent_ready"

    def test_lifecycle_event_str_representation(self):
        """Verify __str__ returns the value."""
        assert str(LifecycleEvent.AGENT_READY) == "agent_ready"
        assert str(LifecycleEvent.BEFORE_LLM_CALL) == "before_llm_call"

    def test_lifecycle_event_count(self):
        """Verify we have exactly 6 lifecycle events."""
        assert len(LifecycleEvent) == 6
