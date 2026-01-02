"""
Unit tests for the TextState class.
"""
import pytest
from autobyteus.agent.streaming.parser.parser_context import ParserContext, ParserConfig
from autobyteus.agent.streaming.parser.states.text_state import TextState
from autobyteus.agent.streaming.parser.states.xml_tag_initialization_state import XmlTagInitializationState
from autobyteus.agent.streaming.parser.states.json_initialization_state import JsonInitializationState
from autobyteus.agent.streaming.parser.events import SegmentType, SegmentEventType


class TestTextStateBasics:
    """Tests for basic TextState functionality."""

    def test_plain_text_emits_text_segment(self):
        """Plain text without triggers emits text segment."""
        ctx = ParserContext()
        ctx.append("Hello World")
        
        state = TextState(ctx)
        ctx.current_state = state
        state.run()
        
        events = ctx.get_and_clear_events()
        assert len(events) == 3  # START, CONTENT, END
        
        assert events[0].event_type == SegmentEventType.START
        assert events[0].segment_type == SegmentType.TEXT
        
        assert events[1].event_type == SegmentEventType.CONTENT
        assert events[1].payload["delta"] == "Hello World"
        
        assert events[2].event_type == SegmentEventType.END

    def test_empty_buffer_no_events(self):
        """Empty buffer produces no events."""
        ctx = ParserContext()
        
        state = TextState(ctx)
        ctx.current_state = state
        state.run()
        
        events = ctx.get_and_clear_events()
        assert len(events) == 0


class TestTextStateXmlTrigger:
    """Tests for XML tag trigger detection."""

    def test_less_than_triggers_xml_state(self):
        """'<' character triggers transition to XmlTagInitializationState."""
        ctx = ParserContext()
        ctx.append("Hello <tool>")
        
        state = TextState(ctx)
        ctx.current_state = state
        state.run()
        
        # Should have transitioned
        assert isinstance(ctx.current_state, XmlTagInitializationState)
        
        # Should have emitted text before the '<'
        events = ctx.get_and_clear_events()
        assert len(events) == 3  # START, CONTENT("Hello "), END
        assert events[1].payload["delta"] == "Hello "

    def test_less_than_at_start_no_text_emitted(self):
        """'<' at start transitions without emitting empty text."""
        ctx = ParserContext()
        ctx.append("<tool>")
        
        state = TextState(ctx)
        ctx.current_state = state
        state.run()
        
        assert isinstance(ctx.current_state, XmlTagInitializationState)
        
        # No text events should be emitted
        events = ctx.get_and_clear_events()
        assert len(events) == 0

    def test_multiple_text_chunks_before_tag(self):
        """Multiple characters accumulated before tag trigger."""
        ctx = ParserContext()
        ctx.append("abc def ghi<")
        
        state = TextState(ctx)
        ctx.current_state = state
        state.run()
        
        events = ctx.get_and_clear_events()
        assert len(events) == 3
        assert events[1].payload["delta"] == "abc def ghi"


class TestTextStateJsonTrigger:
    """Tests for JSON trigger detection."""

    def test_json_disabled_by_default_strategy_order(self):
        """Default strategy order excludes JSON, so '{' is not a trigger."""
        ctx = ParserContext()  # Default: strategy_order=["xml_tag"]
        ctx.append("Test {json}")
        
        state = TextState(ctx)
        ctx.current_state = state
        state.run()
        
        # Should still be in TextState (no transition)
        # Actually, after run, we stay in same state if no transition
        events = ctx.get_and_clear_events()
        
        # All content should be emitted as text
        assert any(e.payload.get("delta") == "Test {json}" for e in events if e.event_type == SegmentEventType.CONTENT)

    def test_json_enabled_triggers_json_state(self):
        """With JSON strategy enabled, '{' triggers JSON state."""
        config = ParserConfig(parse_tool_calls=True, strategy_order=["json_tool"])
        ctx = ParserContext(config)
        ctx.append("Before {json}")
        
        state = TextState(ctx)
        ctx.current_state = state
        state.run()
        
        # Should have transitioned to JsonInitializationState
        assert isinstance(ctx.current_state, JsonInitializationState)
        
        # Should have emitted text before the '{'
        events = ctx.get_and_clear_events()
        assert len(events) == 3
        assert events[1].payload["delta"] == "Before "

    def test_json_disabled_when_parse_tool_calls_false(self):
        """With parse_tool_calls=False, '{' is not a trigger."""
        config = ParserConfig(parse_tool_calls=False, strategy_order=["json_tool"])
        ctx = ParserContext(config)
        ctx.append("Test {json}")
        
        state = TextState(ctx)
        ctx.current_state = state
        state.run()
        
        events = ctx.get_and_clear_events()
        # All content should be emitted as text
        assert any(e.payload.get("delta") == "Test {json}" for e in events if e.event_type == SegmentEventType.CONTENT)


class TestTextStateStreaming:
    """Tests simulating streaming behavior."""

    def test_partial_buffer_then_more_data(self):
        """Text state handles partial data correctly."""
        ctx = ParserContext()
        
        # First chunk - no trigger
        ctx.append("Hello ")
        state = TextState(ctx)
        ctx.current_state = state
        state.run()
        
        events = ctx.get_and_clear_events()
        assert len(events) == 3
        assert events[1].payload["delta"] == "Hello "
        
        # Second chunk - still no trigger
        ctx.append("World")
        state = TextState(ctx)
        ctx.current_state = state
        state.run()
        
        events = ctx.get_and_clear_events()
        assert len(events) == 3
        assert events[1].payload["delta"] == "World"

    def test_trigger_arrives_in_later_chunk(self):
        """Trigger character can arrive in a later chunk."""
        ctx = ParserContext()
        
        # First chunk
        ctx.append("Setup text")
        state = TextState(ctx)
        ctx.current_state = state
        state.run()
        ctx.get_and_clear_events()  # Clear
        
        # Second chunk with trigger
        ctx.append(" and then <tool")
        state = TextState(ctx)
        ctx.current_state = state
        state.run()
        
        assert isinstance(ctx.current_state, XmlTagInitializationState)
        events = ctx.get_and_clear_events()
        assert events[1].payload["delta"] == " and then "


class TestTextStateFinalize:
    """Tests for finalize behavior."""

    def test_finalize_does_nothing(self):
        """Finalize on TextState is a no-op."""
        ctx = ParserContext()
        state = TextState(ctx)
        
        # Should not raise
        state.finalize()
        
        events = ctx.get_and_clear_events()
        assert len(events) == 0
