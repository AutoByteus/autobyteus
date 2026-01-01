"""
Unit tests for ToolInvocationAdapter.
"""
import pytest
from autobyteus.agent.streaming.parser.events import PartStartEvent, PartDeltaEvent, PartEndEvent
from autobyteus.agent.streaming.parser.invocation_adapter import ToolInvocationAdapter


class TestToolInvocationAdapterBasics:
    """Basic functionality tests."""

    def test_complete_tool_part_creates_invocation(self):
        """Complete tool part lifecycle creates ToolInvocation."""
        adapter = ToolInvocationAdapter()
        
        # Simulate tool part: START → DELTA → END
        events = [
            PartStartEvent(part_id="p1", part_type="tool_call", metadata={"tool_name": "read_file"}),
            PartDeltaEvent(part_id="p1", delta="<arguments><path>/src/main.py</path></arguments>"),
            PartEndEvent(part_id="p1", metadata={"tool_name": "read_file", "arguments": {"path": "/src/main.py"}})
        ]
        
        invocations = adapter.process_events(events)
        
        assert len(invocations) == 1
        assert invocations[0].id == "p1"  # part_id becomes invocationId
        assert invocations[0].name == "read_file"
        assert invocations[0].arguments == {"path": "/src/main.py"}

    def test_part_id_depends_invocation_id(self):
        """Verify part_id is used as invocationId."""
        adapter = ToolInvocationAdapter()
        
        start = PartStartEvent(part_id="my-unique-id-123", part_type="tool_call", metadata={"tool_name": "write_file"})
        end = PartEndEvent(
            part_id="my-unique-id-123",
            metadata={"tool_name": "write_file", "arguments": {"path": "/out.txt", "content": "data"}}
        )
        
        adapter.process_event(start)
        result = adapter.process_event(end)
        
        assert result is not None
        assert result.id == "my-unique-id-123"

    def test_non_tool_parts_ignored(self):
        """Text and other parts don't create invocations."""
        adapter = ToolInvocationAdapter()
        
        events = [
            PartStartEvent(part_id="p1", part_type="text"),
            PartDeltaEvent(part_id="p1", delta="hello"),
            PartEndEvent(part_id="p1"),
            # Text parts should be ignored
            PartStartEvent(part_id="p2", part_type="text"),
            PartEndEvent(part_id="p2"),
        ]
        
        invocations = adapter.process_events(events)
        assert len(invocations) == 0

    def test_multiple_tool_parts(self):
        """Multiple tool parts create multiple invocations."""
        adapter = ToolInvocationAdapter()
        
        events = [
            PartStartEvent(part_id="p1", part_type="tool_call", metadata={"tool_name": "tool_a"}),
            PartEndEvent(part_id="p1", metadata={"tool_name": "tool_a", "arguments": {"x": 1}}),
            PartStartEvent(part_id="p2", part_type="tool_call", metadata={"tool_name": "tool_b"}),
            PartEndEvent(part_id="p2", metadata={"tool_name": "tool_b", "arguments": {"y": 2}}),
        ]
        
        invocations = adapter.process_events(events)
        
        assert len(invocations) == 2
        assert invocations[0].id == "p1"
        assert invocations[0].name == "tool_a"
        assert invocations[1].id == "p2"
        assert invocations[1].name == "tool_b"


class TestToolInvocationAdapterState:
    """State management tests."""

    def test_active_parts_tracked(self):
        """Active parts are tracked until END."""
        adapter = ToolInvocationAdapter()
        
        adapter.process_event(PartStartEvent(part_id="p1", part_type="tool_call", metadata={"tool_name": "test"}))
        
        assert "p1" in adapter.get_active_part_ids()
        
        adapter.process_event(PartEndEvent(part_id="p1", metadata={"tool_name": "test", "arguments": {}}))
        
        assert "p1" not in adapter.get_active_part_ids()

    def test_reset_clears_state(self):
        """Reset clears all tracking."""
        adapter = ToolInvocationAdapter()
        
        adapter.process_event(PartStartEvent(part_id="p1", part_type="tool_call", metadata={"tool_name": "test"}))
        adapter.process_event(PartStartEvent(part_id="p2", part_type="tool_call", metadata={"tool_name": "test"}))
        
        assert len(adapter.get_active_part_ids()) == 2
        
        adapter.reset()
        
        assert len(adapter.get_active_part_ids()) == 0


class TestToolInvocationAdapterEdgeCases:
    """Edge case tests."""

    def test_end_without_start_ignored(self):
        """END without prior START is ignored."""
        adapter = ToolInvocationAdapter()
        
        result = adapter.process_event(PartEndEvent(part_id="unknown_part"))
        
        assert result is None

    def test_delta_without_start_ignored(self):
        """DELTA without prior START is ignored."""
        adapter = ToolInvocationAdapter()
        
        result = adapter.process_event(PartDeltaEvent(part_id="unknown_part", delta="data"))
        
        assert result is None

    def test_incomplete_part_no_invocation(self):
        """Incomplete part (no END) doesn't create invocation."""
        adapter = ToolInvocationAdapter()
        
        adapter.process_event(PartStartEvent(part_id="p1", part_type="tool_call", metadata={"tool_name": "test"}))
        adapter.process_event(PartDeltaEvent(part_id="p1", delta="content"))
        # No END event
        
        assert len(adapter.get_active_part_ids()) == 1
        # No invocation created yet (process_event returns None for start/delta)
