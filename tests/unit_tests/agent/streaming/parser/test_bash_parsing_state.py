"""
Unit tests for BashParsingState.
"""
import pytest
from autobyteus.agent.streaming.parser.parser_context import ParserContext
from autobyteus.agent.streaming.parser.events import SegmentType, SegmentEventType
from autobyteus.agent.streaming.parser.states.bash_parsing_state import BashParsingState
from autobyteus.agent.streaming.parser.states.text_state import TextState


class TestBashParsingStateBasics:
    """Tests for basic BashParsingState functionality."""

    def test_simple_bash_command(self):
        """Simple bash command is parsed correctly."""
        ctx = ParserContext()
        ctx.append("ls -la</bash>")
        
        state = BashParsingState(ctx, "<bash>")
        ctx.current_state = state
        state.run()
        
        events = ctx.get_and_clear_events()
        
        # Find START event
        start_events = [e for e in events if e.event_type == SegmentEventType.START]
        assert len(start_events) == 1
        assert start_events[0].segment_type == SegmentType.BASH
        
        # Find CONTENT event with command
        content_events = [e for e in events if e.event_type == SegmentEventType.CONTENT]
        content = "".join(e.payload.get("delta", "") for e in content_events)
        assert "ls -la" in content
        
        # Should transition to TextState
        assert isinstance(ctx.current_state, TextState)

    def test_bash_ignores_attributes(self):
        """Bash tag handles attributes gracefully (ignores them)."""
        ctx = ParserContext()
        ctx.append("ls -la</bash>")
        
        # Even if attributes are present, they are ignored
        state = BashParsingState(ctx, "<bash description='List files'>")
        ctx.current_state = state
        state.run()
        
        events = ctx.get_and_clear_events()
        start_events = [e for e in events if e.event_type == SegmentEventType.START]
        # No metadata extracted
        metadata = start_events[0].payload.get("metadata")
        assert metadata is None or metadata == {}

    def test_bash_preserves_comments(self):
        """Bash content including comments is preserved exactly as is."""
        ctx = ParserContext()
        ctx.append("# Install deps\nnpm install</bash>")
        
        state = BashParsingState(ctx, "<bash>")
        ctx.current_state = state
        state.run()
        
        events = ctx.get_and_clear_events()
        
        # Content should include the full text including comment
        content_events = [e for e in events if e.event_type == SegmentEventType.CONTENT]
        content = "".join(e.payload.get("delta", "") for e in content_events)
        assert "# Install deps" in content
        assert "npm install" in content


class TestBashParsingStateStreaming:
    """Tests for streaming behavior in BashParsingState."""

    def test_partial_tag_held_back(self):
        """Partial closing tags are not emitted prematurely."""
        ctx = ParserContext()
        # Use longer content so we can verify holdback works
        ctx.append("echo hello world</ba")  # Partial closing tag
        
        state = BashParsingState(ctx, "<bash>")
        ctx.current_state = state
        state.run()
        
        events = ctx.get_and_clear_events()
        
        # Safe streaming holds back len("</bash>")-1 = 6 chars from end
        content_events = [e for e in events if e.event_type == SegmentEventType.CONTENT]
        content = "".join(e.payload.get("delta", "") for e in content_events)
        assert "</ba" not in content
        assert "echo hello" in content  # Early content should be emitted


class TestBashParsingStateFinalize:
    """Tests for finalize behavior in BashParsingState."""

    def test_finalize_incomplete_bash(self):
        """Incomplete bash at stream end is closed properly."""
        ctx = ParserContext()
        ctx.append("partial command")
        
        state = BashParsingState(ctx, "<bash>")
        ctx.current_state = state
        state.run()
        state.finalize()
        
        events = ctx.get_and_clear_events()
        
        # Should have END event
        end_events = [e for e in events if e.event_type == SegmentEventType.END]
        assert len(end_events) == 1
