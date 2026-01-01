"""
Unit tests for FileParsingState.
"""
import pytest
from autobyteus.agent.streaming.parser.parser_context import ParserContext
from autobyteus.agent.streaming.parser.events import SegmentType, SegmentEventType
from autobyteus.agent.streaming.parser.states.file_parsing_state import FileParsingState
from autobyteus.agent.streaming.parser.states.text_state import TextState


class TestFileParsingStateBasics:
    """Tests for basic FileParsingState functionality."""

    def test_simple_file_content(self):
        """File with path attribute parses correctly."""
        ctx = ParserContext()
        ctx.append("print('hello')</file>")
        
        state = FileParsingState(ctx, "<file path='/test.py'>")
        ctx.current_state = state
        state.run()
        
        events = ctx.get_and_clear_events()
        
        # Find START event
        start_events = [e for e in events if e.event_type == SegmentEventType.START]
        assert len(start_events) == 1
        assert start_events[0].segment_type == SegmentType.FILE
        assert start_events[0].payload.get("metadata", {}).get("path") == "/test.py"
        
        # Find CONTENT event
        content_events = [e for e in events if e.event_type == SegmentEventType.CONTENT]
        content = "".join(e.payload.get("delta", "") for e in content_events)
        assert content == "print('hello')"
        
        # Should transition to TextState
        assert isinstance(ctx.current_state, TextState)

    def test_file_no_path_treated_as_text(self):
        """File tag without path is treated as text."""
        ctx = ParserContext()
        ctx.append("content</file>")
        
        state = FileParsingState(ctx, "<file>")  # No path
        ctx.current_state = state
        state.run()
        
        events = ctx.get_and_clear_events()
        
        # Should emit text, not file segment
        start_events = [e for e in events if e.event_type == SegmentEventType.START]
        assert len(start_events) == 1
        assert start_events[0].segment_type == SegmentType.TEXT


class TestFileParsingStateStreaming:
    """Tests for streaming behavior in FileParsingState."""

    def test_partial_tag_held_back(self):
        """Partial closing tags are not emitted prematurely."""
        ctx = ParserContext()
        # Use longer content so we can verify holdback works
        ctx.append("hello world content</fi")  # Partial closing tag
        
        state = FileParsingState(ctx, "<file path='/a.py'>")
        ctx.current_state = state
        state.run()
        
        events = ctx.get_and_clear_events()
        
        # START event should exist
        start_events = [e for e in events if e.event_type == SegmentEventType.START]
        assert len(start_events) == 1
        
        # CONTENT should NOT include "</fi" (held back)
        # Safe streaming holds back len("</file>")-1 = 6 chars from end
        content_events = [e for e in events if e.event_type == SegmentEventType.CONTENT]
        content = "".join(e.payload.get("delta", "") for e in content_events)
        assert "</fi" not in content
        assert "hello world" in content  # Early content should be emitted


class TestFileParsingStateFinalize:
    """Tests for finalize behavior in FileParsingState."""

    def test_finalize_emits_remaining(self):
        """Finalize emits remaining content."""
        ctx = ParserContext()
        ctx.append("partial content")
        
        state = FileParsingState(ctx, "<file path='/a.py'>")
        ctx.current_state = state
        state.run()
        state.finalize()
        
        events = ctx.get_and_clear_events()
        
        # Should have END event
        end_events = [e for e in events if e.event_type == SegmentEventType.END]
        assert len(end_events) == 1
