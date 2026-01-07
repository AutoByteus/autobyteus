"""
Unit tests for StreamingResponseHandler.
"""
import pytest
from autobyteus.agent.streaming.parsing_streaming_response_handler import ParsingStreamingResponseHandler
from autobyteus.agent.streaming.parser.events import SegmentEvent, SegmentType, SegmentEventType


class TestStreamingResponseHandlerBasics:
    """Basic functionality tests."""

    def test_feed_text_emits_events(self):
        """Feeding text produces SegmentEvents."""
        handler = ParsingStreamingResponseHandler()
        events = handler.feed("Hello world")
        
        # Should have at least a text segment
        assert len(events) > 0

    def test_feed_and_finalize(self):
        """Full lifecycle produces complete events."""
        handler = ParsingStreamingResponseHandler()
        events1 = handler.feed("Test message")
        events2 = handler.finalize()
        
        all_events = handler.get_all_events()
        assert len(all_events) > 0

    def test_double_finalize_returns_empty(self):
        """Second finalize returns empty list."""
        handler = ParsingStreamingResponseHandler()
        handler.feed("test")
        handler.finalize()
        events = handler.finalize()
        
        assert events == []

    def test_feed_after_finalize_raises(self):
        """Feeding after finalize raises error."""
        handler = ParsingStreamingResponseHandler()
        handler.finalize()
        
        with pytest.raises(RuntimeError):
            handler.feed("more data")


class TestParsingStreamingResponseHandlerCallbacks:
    """Callback tests."""

    def test_on_segment_event_called(self):
        """on_segment_event callback is invoked for each event."""
        received = []
        
        handler = ParsingStreamingResponseHandler(
            on_segment_event=lambda e: received.append(e)
        )
        handler.feed("Hello")
        handler.finalize()
        
        assert len(received) > 0
        assert all(isinstance(e, SegmentEvent) for e in received)

    def test_on_tool_invocation_called(self):
        """on_tool_invocation callback is invoked for tool segments."""
        invocations = []
        
        handler = ParsingStreamingResponseHandler(
            on_tool_invocation=lambda inv: invocations.append(inv)
        )
        
        # Feed a tool call with proper XML format
        handler.feed('<tool name="test_tool"><key>value</key></tool>')
        handler.finalize()
        
        assert len(invocations) == 1
        assert invocations[0].name == "test_tool"

    def test_callback_error_does_not_crash(self):
        """Error in callback is logged but doesn't crash handler."""
        def bad_callback(event):
            raise Exception("Callback error!")
        
        handler = ParsingStreamingResponseHandler(on_segment_event=bad_callback)
        # Should not raise
        handler.feed("test")
        handler.finalize()


class TestParsingStreamingResponseHandlerToolIntegration:
    """Tool invocation integration tests."""

    def test_tool_segment_creates_invocation(self):
        """Tool segment creates ToolInvocation with correct segment_id."""
        handler = ParsingStreamingResponseHandler()
        
        # Use proper XML argument format
        handler.feed('<tool name="read_file"><path>/test.py</path></tool>')
        handler.finalize()
        
        invocations = handler.get_all_invocations()
        assert len(invocations) == 1
        assert invocations[0].name == "read_file"
        assert invocations[0].arguments == {"path": "/test.py"}

    def test_multiple_tools_create_multiple_invocations(self):
        """Multiple tool segments create multiple invocations."""
        handler = ParsingStreamingResponseHandler()
        
        handler.feed('Some text <tool name="tool_a"><a>1</a></tool>')
        handler.feed(' more text <tool name="tool_b"><b>2</b></tool>')
        handler.finalize()
        
        invocations = handler.get_all_invocations()
        assert len(invocations) == 2

    def test_segment_id_is_invocation_id(self):
        """Verify segment_id becomes invocationId."""
        handler = ParsingStreamingResponseHandler()
        
        handler.feed('<tool name="test"></tool>')
        handler.finalize()
        
        events = handler.get_all_events()
        invocations = handler.get_all_invocations()
        
        # Find the tool START event
        tool_start = next((e for e in events if e.segment_type == SegmentType.TOOL_CALL), None)
        
        if tool_start:
            # The invocation should have the same ID
            assert invocations[0].id == tool_start.segment_id


class TestParsingStreamingResponseHandlerReset:
    """Reset functionality tests."""

    def test_reset_clears_state(self):
        """Reset allows handler reuse."""
        handler = ParsingStreamingResponseHandler()
        
        handler.feed("test data")
        handler.finalize()
        
        assert len(handler.get_all_events()) > 0
        
        handler.reset()
        
        assert len(handler.get_all_events()) == 0
        assert len(handler.get_all_invocations()) == 0
        
        # Can feed again
        handler.feed("new data")
        handler.finalize()
        assert len(handler.get_all_events()) > 0
