"""
Unit tests for ToolInvocationAdapter.
"""
import pytest
from autobyteus.agent.streaming.parser.events import SegmentEvent, SegmentType, SegmentEventType
from autobyteus.agent.streaming.parser.invocation_adapter import ToolInvocationAdapter


class TestToolInvocationAdapterBasics:
    """Basic functionality tests."""

    def test_complete_tool_segment_creates_invocation(self):
        """Complete tool segment lifecycle creates ToolInvocation."""
        adapter = ToolInvocationAdapter()
        
        # Simulate tool segment: START → CONTENT → END
        events = [
            SegmentEvent.start("seg_5", SegmentType.TOOL_CALL, tool_name="read_file"),
            SegmentEvent.content("seg_5", "<arguments><path>/src/main.py</path></arguments>"),
            SegmentEvent(
                event_type=SegmentEventType.END,
                segment_id="seg_5",
                payload={"metadata": {"tool_name": "read_file", "arguments": {"path": "/src/main.py"}}}
            )
        ]
        
        invocations = adapter.process_events(events)
        
        assert len(invocations) == 1
        assert invocations[0].id == "seg_5"  # segment_id becomes invocationId
        assert invocations[0].name == "read_file"
        assert invocations[0].arguments == {"path": "/src/main.py"}

    def test_segment_id_becomes_invocation_id(self):
        """Verify segment_id is used as invocationId."""
        adapter = ToolInvocationAdapter()
        
        start = SegmentEvent.start("my-unique-id-123", SegmentType.TOOL_CALL, tool_name="write_file")
        end = SegmentEvent(
            event_type=SegmentEventType.END,
            segment_id="my-unique-id-123",
            payload={"metadata": {"tool_name": "write_file", "arguments": {"path": "/out.txt", "content": "data"}}}
        )
        
        adapter.process_event(start)
        result = adapter.process_event(end)
        
        assert result is not None
        assert result.id == "my-unique-id-123"

    def test_non_tool_segments_ignored(self):
        """Text segments don't create invocations."""
        adapter = ToolInvocationAdapter()
        
        events = [
            SegmentEvent.start("seg_1", SegmentType.TEXT),
            SegmentEvent.content("seg_1", "hello"),
            SegmentEvent.end("seg_1"),
        ]
        
        invocations = adapter.process_events(events)
        assert len(invocations) == 0

    def test_file_segment_creates_write_file_invocation(self):
        """File segments create write_file invocations."""
        adapter = ToolInvocationAdapter()

        events = [
            SegmentEvent.start("seg_2", SegmentType.FILE, path="/test.py"),
            SegmentEvent.content("seg_2", "code"),
            SegmentEvent.end("seg_2"),
        ]

        invocations = adapter.process_events(events)
        assert len(invocations) == 1
        assert invocations[0].name == "write_file"
        assert invocations[0].arguments == {"path": "/test.py", "content": "code"}

    def test_bash_segment_creates_run_terminal_cmd_invocation(self):
        """Bash segments create run_terminal_cmd invocations."""
        adapter = ToolInvocationAdapter()

        events = [
            SegmentEvent.start("seg_3", SegmentType.BASH),
            SegmentEvent.content("seg_3", "ls -la"),
            SegmentEvent.end("seg_3"),
        ]

        invocations = adapter.process_events(events)
        assert len(invocations) == 1
        assert invocations[0].name == "run_terminal_cmd"
        assert invocations[0].arguments == {"command": "ls -la"}

    def test_multiple_tool_segments(self):
        """Multiple tool segments create multiple invocations."""
        adapter = ToolInvocationAdapter()
        
        events = [
            SegmentEvent.start("seg_1", SegmentType.TOOL_CALL, tool_name="tool_a"),
            SegmentEvent(event_type=SegmentEventType.END, segment_id="seg_1", 
                        payload={"metadata": {"tool_name": "tool_a", "arguments": {"x": 1}}}),
            SegmentEvent.start("seg_2", SegmentType.TOOL_CALL, tool_name="tool_b"),
            SegmentEvent(event_type=SegmentEventType.END, segment_id="seg_2",
                        payload={"metadata": {"tool_name": "tool_b", "arguments": {"y": 2}}}),
        ]
        
        invocations = adapter.process_events(events)
        
        assert len(invocations) == 2
        assert invocations[0].id == "seg_1"
        assert invocations[0].name == "tool_a"
        assert invocations[1].id == "seg_2"
        assert invocations[1].name == "tool_b"

    def test_file_segment_without_path_is_ignored(self):
        """File segments without path do not create invocations."""
        adapter = ToolInvocationAdapter()

        events = [
            SegmentEvent.start("seg_x", SegmentType.FILE),
            SegmentEvent.content("seg_x", "code"),
            SegmentEvent.end("seg_x"),
        ]

        invocations = adapter.process_events(events)
        assert len(invocations) == 0


class TestToolInvocationAdapterState:
    """State management tests."""

    def test_active_segments_tracked(self):
        """Active segments are tracked until END."""
        adapter = ToolInvocationAdapter()
        
        adapter.process_event(SegmentEvent.start("seg_1", SegmentType.TOOL_CALL, tool_name="test"))
        
        assert "seg_1" in adapter.get_active_segment_ids()
        
        adapter.process_event(SegmentEvent(
            event_type=SegmentEventType.END, segment_id="seg_1",
            payload={"metadata": {"tool_name": "test", "arguments": {}}}
        ))
        
        assert "seg_1" not in adapter.get_active_segment_ids()

    def test_reset_clears_state(self):
        """Reset clears all tracking."""
        adapter = ToolInvocationAdapter()
        
        adapter.process_event(SegmentEvent.start("seg_1", SegmentType.TOOL_CALL, tool_name="test"))
        adapter.process_event(SegmentEvent.start("seg_2", SegmentType.TOOL_CALL, tool_name="test"))
        
        assert len(adapter.get_active_segment_ids()) == 2
        
        adapter.reset()
        
        assert len(adapter.get_active_segment_ids()) == 0


class TestToolInvocationAdapterEdgeCases:
    """Edge case tests."""

    def test_end_without_start_ignored(self):
        """END without prior START is ignored."""
        adapter = ToolInvocationAdapter()
        
        result = adapter.process_event(SegmentEvent.end("unknown_seg"))
        
        assert result is None

    def test_content_without_start_ignored(self):
        """CONTENT without prior START is ignored."""
        adapter = ToolInvocationAdapter()
        
        result = adapter.process_event(SegmentEvent.content("unknown_seg", "data"))
        
        assert result is None

    def test_incomplete_segment_no_invocation(self):
        """Incomplete segment (no END) doesn't create invocation."""
        adapter = ToolInvocationAdapter()
        
        adapter.process_event(SegmentEvent.start("seg_1", SegmentType.TOOL_CALL, tool_name="test"))
        adapter.process_event(SegmentEvent.content("seg_1", "content"))
        # No END event
        
        assert len(adapter.get_active_segment_ids()) == 1
        # No invocation created yet
