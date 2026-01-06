"""
Unit tests for CustomXmlTagRunBashParsingState.
"""
import pytest
from autobyteus.agent.streaming.parser.parser_context import ParserContext
from autobyteus.agent.streaming.parser.events import SegmentType, SegmentEventType
from autobyteus.agent.streaming.parser.states.custom_xml_tag_run_bash_parsing_state import CustomXmlTagRunBashParsingState
from autobyteus.agent.streaming.parser.states.text_state import TextState


class TestCustomXmlTagRunBashParsingStateBasics:
    """Tests for basic CustomXmlTagRunBashParsingState functionality."""

    def test_simple_command(self):
        """Simple command is parsed correctly."""
        ctx = ParserContext()
        ctx.append("ls -la</run_bash>")
        
        state = CustomXmlTagRunBashParsingState(ctx, "<run_bash>")
        ctx.current_state = state
        state.run()
        
        events = ctx.get_and_clear_events()
        
        # Find START event
        start_events = [e for e in events if e.event_type == SegmentEventType.START]
        assert len(start_events) == 1
        assert start_events[0].segment_type == SegmentType.RUN_BASH
        
        # Find CONTENT event with command
        content_events = [e for e in events if e.event_type == SegmentEventType.CONTENT]
        content = "".join(e.payload.get("delta", "") for e in content_events)
        assert "ls -la" in content
        
        # Should transition to TextState
        assert isinstance(ctx.current_state, TextState)

    def test_ignores_attributes(self):
        """Tag handles attributes gracefully (ignores them)."""
        ctx = ParserContext()
        ctx.append("ls -la</run_bash>")
        
        # Even if attributes are present, they are ignored
        state = CustomXmlTagRunBashParsingState(ctx, "<run_bash description='List files'>")
        ctx.current_state = state
        state.run()
        
        events = ctx.get_and_clear_events()
        start_events = [e for e in events if e.event_type == SegmentEventType.START]
        # No metadata extracted
        metadata = start_events[0].payload.get("metadata")
        assert metadata is None or metadata == {}

    def test_preserves_comments(self):
        """Content including comments is preserved exactly as is."""
        ctx = ParserContext()
        ctx.append("# Install deps\nnpm install</run_bash>")
        
        state = CustomXmlTagRunBashParsingState(ctx, "<run_bash>")
        ctx.current_state = state
        state.run()
        
        events = ctx.get_and_clear_events()
        
        # Content should include the full text including comment
        content_events = [e for e in events if e.event_type == SegmentEventType.CONTENT]
        content = "".join(e.payload.get("delta", "") for e in content_events)
        assert "# Install deps" in content
        assert "npm install" in content


class TestCustomXmlTagRunBashParsingStateStreaming:
    """Tests for streaming behavior in CustomXmlTagRunBashParsingState."""

    def test_partial_tag_held_back(self):
        """Partial closing tags are not emitted prematurely."""
        ctx = ParserContext()
        # Use longer content so we can verify holdback works
        # </run_bash> is 11 chars, so holdback is 10 chars
        ctx.append("echo hello world command</run")  # Partial closing tag
        
        state = CustomXmlTagRunBashParsingState(ctx, "<run_bash>")
        ctx.current_state = state
        state.run()
        
        events = ctx.get_and_clear_events()
        
        content_events = [e for e in events if e.event_type == SegmentEventType.CONTENT]
        content = "".join(e.payload.get("delta", "") for e in content_events)
        assert "</run" not in content
        assert "echo hello" in content  # Early content should be emitted


class TestCustomXmlTagRunBashParsingStateFinalize:
    """Tests for finalize behavior in CustomXmlTagRunBashParsingState."""

    def test_finalize_incomplete(self):
        """Incomplete command at stream end is closed properly."""
        ctx = ParserContext()
        ctx.append("partial command")
        
        state = CustomXmlTagRunBashParsingState(ctx, "<run_bash>")
        ctx.current_state = state
        state.run()
        state.finalize()
        
        events = ctx.get_and_clear_events()
        
        # Should have END event
        end_events = [e for e in events if e.event_type == SegmentEventType.END]
        assert len(end_events) == 1
