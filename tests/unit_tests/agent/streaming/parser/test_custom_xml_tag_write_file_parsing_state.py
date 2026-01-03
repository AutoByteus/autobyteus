"""
Unit tests for CustomXmlTagWriteFileParsingState.
"""
import pytest
from autobyteus.agent.streaming.parser.parser_context import ParserContext
from autobyteus.agent.streaming.parser.states.text_state import TextState
from autobyteus.agent.streaming.parser.states.custom_xml_tag_write_file_parsing_state import CustomXmlTagWriteFileParsingState
from autobyteus.agent.streaming.parser.events import SegmentType, SegmentEventType


class TestCustomXmlTagWriteFileParsingStateBasics:
    """Tests for basic CustomXmlTagWriteFileParsingState functionality."""

    def test_simple_file_content(self):
        """File with path attribute parses correctly."""
        ctx = ParserContext()
        ctx.append("print('hello')</write_file>")
        
        state = CustomXmlTagWriteFileParsingState(ctx, "<write_file path='/test.py'>")
        ctx.current_state = state
        state.run()
        
        events = ctx.get_and_clear_events()
        
        # Find START event
        start_events = [e for e in events if e.event_type == SegmentEventType.START]
        assert len(start_events) == 1
        assert start_events[0].segment_type == SegmentType.WRITE_FILE
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
        ctx.append("content</write_file>")
        
        state = CustomXmlTagWriteFileParsingState(ctx, "<write_file>")  # No path
        ctx.current_state = state
        state.run()
        
        events = ctx.get_and_clear_events()
        
        # Should emit text, not file segment
        start_events = [e for e in events if e.event_type == SegmentEventType.START]
        assert len(start_events) == 1
        assert start_events[0].segment_type == SegmentType.TEXT


class TestCustomXmlTagWriteFileParsingStateStreaming:
    """Tests for streaming behavior in CustomXmlTagWriteFileParsingState."""

    def test_partial_tag_held_back(self):
        """Partial closing tags are not emitted prematurely."""
        ctx = ParserContext()
        # Use longer content so we can verify holdback works
        ctx.append("hello world content</wri")  # Partial closing tag
        
        state = CustomXmlTagWriteFileParsingState(ctx, "<write_file path='/a.py'>")
        ctx.current_state = state
        state.run()
        
        events = ctx.get_and_clear_events()
        
        # START event should exist
        start_events = [e for e in events if e.event_type == SegmentEventType.START]
        assert len(start_events) == 1
        
        # CONTENT should NOT include "</wri" (held back)
        content_events = [e for e in events if e.event_type == SegmentEventType.CONTENT]
        content = "".join(e.payload.get("delta", "") for e in content_events)
        assert "</wri" not in content
        assert "hello world" in content  # Early content should be emitted


class TestCustomXmlTagWriteFileParsingStateFinalize:
    """Tests for finalize behavior in CustomXmlTagWriteFileParsingState."""

    def test_finalize_emits_remaining(self):
        """Finalize emits remaining content."""
        ctx = ParserContext()
        ctx.append("partial content")
        
        state = CustomXmlTagWriteFileParsingState(ctx, "<write_file path='/a.py'>")
        ctx.current_state = state
        state.run()
        state.finalize()
        
        events = ctx.get_and_clear_events()
        
        # Should have END event
        end_events = [e for e in events if e.event_type == SegmentEventType.END]
        assert len(end_events) == 1
