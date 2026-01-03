"""
Unit tests for the ParserContext class.
"""
import pytest
from autobyteus.agent.streaming.parser.parser_context import ParserContext, ParserConfig
from autobyteus.agent.streaming.parser.events import SegmentType, SegmentEventType


class TestParserConfig:
    """Tests for ParserConfig."""

    def test_default_config(self):
        """Default config has expected values."""
        config = ParserConfig()
        assert config.parse_tool_calls is True
        assert config.strategy_order == ["xml_tag"]

    def test_custom_config(self):
        """Custom config values are respected."""
        config = ParserConfig(parse_tool_calls=False, strategy_order=["json_tool"])
        assert config.parse_tool_calls is False
        assert config.strategy_order == ["json_tool"]


class TestParserContextInit:
    """Tests for ParserContext initialization."""

    def test_default_initialization(self):
        """Context initializes with default config."""
        ctx = ParserContext()
        assert ctx.parse_tool_calls is True
        assert ctx.config.strategy_order == ["xml_tag"]
        assert ctx.has_more_chars() is False
        assert ctx.get_current_segment_id() is None

    def test_custom_config_initialization(self):
        """Context respects custom config."""
        config = ParserConfig(parse_tool_calls=False)
        ctx = ParserContext(config)
        assert ctx.parse_tool_calls is False


class TestParserContextScanner:
    """Tests for scanner delegation."""

    def test_append_and_peek(self):
        """Append and peek work correctly."""
        ctx = ParserContext()
        ctx.append("hello")
        assert ctx.peek_char() == "h"

    def test_advance(self):
        """Advance moves cursor."""
        ctx = ParserContext()
        ctx.append("abc")
        ctx.advance()
        assert ctx.peek_char() == "b"

    def test_advance_by(self):
        """Advance by multiple positions."""
        ctx = ParserContext()
        ctx.append("hello world")
        ctx.advance_by(6)
        assert ctx.peek_char() == "w"

    def test_has_more_chars(self):
        """Has more chars detection."""
        ctx = ParserContext()
        assert ctx.has_more_chars() is False
        ctx.append("a")
        assert ctx.has_more_chars() is True
        ctx.advance()
        assert ctx.has_more_chars() is False

    def test_get_set_position(self):
        """Get and set position."""
        ctx = ParserContext()
        ctx.append("hello")
        ctx.advance_by(3)
        assert ctx.get_position() == 3
        ctx.set_position(1)
        assert ctx.get_position() == 1
        assert ctx.peek_char() == "e"

    def test_substring(self):
        """Substring extraction."""
        ctx = ParserContext()
        ctx.append("hello world")
        assert ctx.substring(0, 5) == "hello"
        assert ctx.substring(6) == "world"


class TestParserContextSegmentEmission:
    """Tests for segment event emission."""

    def test_emit_segment_lifecycle(self):
        """Full segment lifecycle emits correct events."""
        ctx = ParserContext()
        
        # Start segment
        seg_id = ctx.emit_segment_start(SegmentType.TEXT)
        assert seg_id == "seg_1"
        assert ctx.get_current_segment_id() == "seg_1"
        assert ctx.get_current_segment_type() == SegmentType.TEXT
        
        # Emit content
        ctx.emit_segment_content("Hello ")
        ctx.emit_segment_content("World")
        assert ctx.get_current_segment_content() == "Hello World"
        
        # End segment
        ended_id = ctx.emit_segment_end()
        assert ended_id == "seg_1"
        assert ctx.get_current_segment_id() is None
        
        # Check events
        events = ctx.get_and_clear_events()
        assert len(events) == 4  # START, CONTENT, CONTENT, END
        
        assert events[0].event_type == SegmentEventType.START
        assert events[0].segment_id == "seg_1"
        assert events[0].segment_type == SegmentType.TEXT
        
        assert events[1].event_type == SegmentEventType.CONTENT
        assert events[1].payload["delta"] == "Hello "
        
        assert events[2].event_type == SegmentEventType.CONTENT
        assert events[2].payload["delta"] == "World"
        
        assert events[3].event_type == SegmentEventType.END
        assert events[3].segment_id == "seg_1"

    def test_emit_segment_with_metadata(self):
        """Segment start with metadata."""
        ctx = ParserContext()
        
        seg_id = ctx.emit_segment_start(
            SegmentType.TOOL_CALL, 
            tool_name="weather_api"
        )
        
        events = ctx.get_events()
        assert len(events) == 1
        assert events[0].payload == {"metadata": {"tool_name": "weather_api"}}

    def test_unique_segment_ids(self):
        """Each segment gets a unique ID."""
        ctx = ParserContext()
        
        id1 = ctx.emit_segment_start(SegmentType.TEXT)
        ctx.emit_segment_end()
        
        id2 = ctx.emit_segment_start(SegmentType.WRITE_FILE)
        ctx.emit_segment_end()
        
        id3 = ctx.emit_segment_start(SegmentType.TOOL_CALL)
        ctx.emit_segment_end()
        
        assert id1 == "seg_1"
        assert id2 == "seg_2"
        assert id3 == "seg_3"

    def test_emit_content_without_segment_raises(self):
        """Emitting content without active segment raises error."""
        ctx = ParserContext()
        
        with pytest.raises(RuntimeError, match="Cannot emit content"):
            ctx.emit_segment_content("test")

    def test_emit_end_without_segment_returns_none(self):
        """Ending without active segment returns None."""
        ctx = ParserContext()
        result = ctx.emit_segment_end()
        assert result is None

    def test_get_and_clear_events(self):
        """Get and clear events empties the queue."""
        ctx = ParserContext()
        ctx.emit_segment_start(SegmentType.TEXT)
        ctx.emit_segment_content("test")
        ctx.emit_segment_end()
        
        events1 = ctx.get_and_clear_events()
        assert len(events1) == 3
        
        events2 = ctx.get_and_clear_events()
        assert len(events2) == 0


class TestParserContextTextHelper:
    """Tests for text segment helper."""

    def test_append_text_segment(self):
        """Append text segment starts a segment and emits content."""
        ctx = ParserContext()
        ctx.append_text_segment("Hello World")
        
        events = ctx.get_and_clear_events()
        assert len(events) == 2
        
        assert events[0].event_type == SegmentEventType.START
        assert events[0].segment_type == SegmentType.TEXT
        
        assert events[1].event_type == SegmentEventType.CONTENT
        assert events[1].payload["delta"] == "Hello World"
        assert ctx.get_current_segment_type() == SegmentType.TEXT

    def test_append_text_segment_reuses_open_segment(self):
        """Subsequent text appends should reuse the open text segment."""
        ctx = ParserContext()
        ctx.append_text_segment("Hello ")
        ctx.get_and_clear_events()

        ctx.append_text_segment("World")
        events = ctx.get_and_clear_events()
        assert len(events) == 1
        assert events[0].event_type == SegmentEventType.CONTENT
        assert events[0].payload["delta"] == "World"

    def test_append_empty_text_segment(self):
        """Empty text segment emits nothing."""
        ctx = ParserContext()
        ctx.append_text_segment("")
        
        events = ctx.get_and_clear_events()
        assert len(events) == 0


class TestParserContextMetadata:
    """Tests for segment metadata management."""

    def test_update_metadata(self):
        """Metadata can be updated during segment parsing."""
        ctx = ParserContext()
        ctx.emit_segment_start(SegmentType.TOOL_CALL, tool_name="test")
        
        assert ctx.get_current_segment_metadata() == {"tool_name": "test"}
        
        ctx.update_current_segment_metadata(arg1="value1")
        
        assert ctx.get_current_segment_metadata() == {
            "tool_name": "test",
            "arg1": "value1"
        }
