"""
Unit tests for IframeParsingState.
"""
import pytest
from autobyteus.agent.streaming.parser.parser_context import ParserContext
from autobyteus.agent.streaming.parser.events import SegmentType, SegmentEventType
from autobyteus.agent.streaming.parser.states.iframe_parsing_state import IframeParsingState
from autobyteus.agent.streaming.parser.states.text_state import TextState


class TestIframeParsingStateBasics:
    """Tests for basic IframeParsingState functionality."""

    def test_simple_html_content(self):
        """HTML content is parsed correctly."""
        ctx = ParserContext()
        ctx.append("<html><body>Hello</body></html>")
        
        state = IframeParsingState(ctx, "<!doctype html>")
        ctx.current_state = state
        state.run()
        
        events = ctx.get_and_clear_events()
        
        # Find START event
        start_events = [e for e in events if e.event_type == SegmentEventType.START]
        assert len(start_events) == 1
        assert start_events[0].segment_type == SegmentType.IFRAME
        
        # Find CONTENT events
        content_events = [e for e in events if e.event_type == SegmentEventType.CONTENT]
        content = "".join(e.payload.get("delta", "") for e in content_events)
        assert "<!doctype html>" in content  # Opening tag is emitted
        assert "<html>" in content
        assert "</html>" in content
        
        # Should transition to TextState
        assert isinstance(ctx.current_state, TextState)


class TestIframeParsingStateStreaming:
    """Tests for streaming behavior in IframeParsingState."""

    def test_partial_tag_held_back(self):
        """Partial closing tags are not emitted prematurely."""
        ctx = ParserContext()
        ctx.append("<html><body>Hello</body></htm")  # Partial closing tag
        
        state = IframeParsingState(ctx, "<!doctype html>")
        ctx.current_state = state
        state.run()
        
        events = ctx.get_and_clear_events()
        
        content_events = [e for e in events if e.event_type == SegmentEventType.CONTENT]
        content = "".join(e.payload.get("delta", "") for e in content_events)
        assert "</htm" not in content


class TestIframeParsingStateFinalize:
    """Tests for finalize behavior in IframeParsingState."""

    def test_finalize_incomplete_html(self):
        """Finalize emits remaining content."""
        ctx = ParserContext()
        ctx.append("<html><body>Hello</body>")  # No closing tag
        
        state = IframeParsingState(ctx, "<!doctype html>")
        ctx.current_state = state
        state.run()
        state.finalize()
        
        events = ctx.get_and_clear_events()
        
        # Should have END event
        end_events = [e for e in events if e.event_type == SegmentEventType.END]
        assert len(end_events) == 1
