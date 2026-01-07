"""
Unit tests for PassThroughStreamingResponseHandler.
"""
from autobyteus.agent.streaming.pass_through_streaming_response_handler import PassThroughStreamingResponseHandler
from autobyteus.agent.streaming.parser.events import SegmentEvent, SegmentType, SegmentEventType

class TestPassThroughStreamingResponseHandler:

    def test_feed_creates_start_and_content(self):
        """First feed creates Start and Content events."""
        handler = PassThroughStreamingResponseHandler()
        events = handler.feed("Hello")
        
        assert len(events) == 2
        assert events[0].event_type == SegmentEventType.START
        assert events[0].segment_type == SegmentType.TEXT
        assert events[1].event_type == SegmentEventType.CONTENT
        assert events[1].payload["delta"] == "Hello"

    def test_subsequent_feed_creates_only_content(self):
        """Subsequent feeds only create Content events."""
        handler = PassThroughStreamingResponseHandler()
        handler.feed("Hello")
        events = handler.feed(" World")
        
        assert len(events) == 1
        assert events[0].event_type == SegmentEventType.CONTENT
        assert events[0].payload["delta"] == " World"

    def test_legacy_tags_are_raw_text(self):
        """Tags like <write_file> are treated as raw text."""
        handler = PassThroughStreamingResponseHandler()
        events = handler.feed("<write_file>")
        
        # Should be start + content (if first)
        assert len(events) == 2
        assert events[1].payload["delta"] == "<write_file>"
        
        # Verify no tool invocations
        assert handler.get_all_invocations() == []

    def test_finalize_emits_end(self):
        """Finalize emits End event."""
        handler = PassThroughStreamingResponseHandler()
        handler.feed("test")
        events = handler.finalize()
        
        assert len(events) == 1
        assert events[0].event_type == SegmentEventType.END

    def test_get_all_invocations_is_empty(self):
        """Never returns invocations."""
        handler = PassThroughStreamingResponseHandler()
        handler.feed('<tool name="foo"></tool>')
        handler.finalize()
        
        assert handler.get_all_invocations() == []
        events = handler.get_all_events()
        # Verify events are just text
        content_events = [e for e in events if e.event_type == SegmentEventType.CONTENT]
        assert content_events[0].payload["delta"] == '<tool name="foo"></tool>'
