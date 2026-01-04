"""
Unit tests for the StreamingParser driver class.
"""
import pytest
from autobyteus.agent.streaming.parser.streaming_parser import (
    StreamingParser, 
    parse_complete_response, 
    extract_segments
)
from autobyteus.agent.streaming.parser.parser_context import ParserConfig
from autobyteus.agent.streaming.parser.events import SegmentType, SegmentEventType


class TestStreamingParserBasics:
    """Tests for basic StreamingParser functionality."""

    def test_simple_text_parsing(self):
        """Parse simple text response."""
        parser = StreamingParser()
        events = parser.feed("Hello, I can help you with that!")
        events.extend(parser.finalize())
        
        # Should have text segment events
        start_events = [e for e in events if e.event_type == SegmentEventType.START]
        assert len(start_events) >= 1
        assert start_events[0].segment_type == SegmentType.TEXT

    def test_empty_input_no_events(self):
        """Empty input produces no events."""
        parser = StreamingParser()
        events = parser.feed("")
        events.extend(parser.finalize())
        
        assert len(events) == 0

    def test_multiple_chunks(self):
        """Parse text arriving in multiple chunks."""
        parser = StreamingParser()
        
        events1 = parser.feed("Hello, ")
        events2 = parser.feed("World!")
        events3 = parser.finalize()
        
        all_events = events1 + events2 + events3
        
        # Should have events
        assert len(all_events) > 0


class TestStreamingParserFileParsing:
    """Tests for write_file tag parsing through the driver."""

    def test_complete_write_file_tag(self):
        """Parse a complete write_file tag."""
        parser = StreamingParser()
        events = parser.feed_and_finalize(
            "Here is the code:<write_file path='/test.py'>print('hello')</write_file>Done!"
        )
        
        segments = extract_segments(events)
        
        # Should have write_file segment
        write_file_segments = [s for s in segments if s["type"] == "write_file"]
        assert len(write_file_segments) >= 1
        assert write_file_segments[0]["metadata"].get("path") == "/test.py"


class TestStreamingParserToolParsing:
    """Tests for tool call parsing through the driver."""

    def test_tool_call_enabled(self):
        """Parse tool call with parsing enabled."""
        config = ParserConfig(parse_tool_calls=True, strategy_order=["xml_tag"])
        parser = StreamingParser(config)
        
        events = parser.feed_and_finalize(
            "Let me check:<tool name='weather'><arguments><city>NYC</city></arguments></tool>"
        )
        
        segments = extract_segments(events)
        tool_segments = [s for s in segments if s["type"] == "tool_call"]
        assert len(tool_segments) >= 1

    def test_tool_call_disabled(self):
        """Tool tags become text when parsing disabled."""
        config = ParserConfig(parse_tool_calls=False)
        parser = StreamingParser(config)
        
        events = parser.feed_and_finalize("<tool name='test'>args</tool>")
        
        segments = extract_segments(events)
        tool_segments = [s for s in segments if s["type"] == "tool_call"]
        assert len(tool_segments) == 0

    def test_json_tool_call_split_across_chunks(self):
        """JSON tool call parsing works across chunks."""
        config = ParserConfig(parse_tool_calls=True, strategy_order=["json_tool"])
        parser = StreamingParser(config)

        chunks = [
            '{"name": "do_something", "arguments": {"x": ',
            '1, "y": "ok"}} trailing'
        ]

        events = []
        for chunk in chunks:
            events.extend(parser.feed(chunk))
        events.extend(parser.finalize())

        tool_start = next(
            (e for e in events if e.event_type == SegmentEventType.START and e.segment_type == SegmentType.TOOL_CALL),
            None,
        )
        assert tool_start is not None

        tool_end = next(
            (e for e in events if e.event_type == SegmentEventType.END and e.segment_id == tool_start.segment_id),
            None,
        )
        assert tool_end is not None
        metadata = tool_end.payload.get("metadata", {})
        assert "arguments" not in metadata


class TestStreamingParserMixedContent:
    """Tests for mixed content responses."""

    def test_text_and_write_file(self):
        """Parse mix of text and write_file."""
        parser = StreamingParser()
        events = parser.feed_and_finalize(
            "Here is the solution:\n<write_file path='/main.py'>print('done')</write_file>\nLet me know!"
        )
        
        segments = extract_segments(events)
        types = set(s["type"] for s in segments)
        
        assert "text" in types
        assert "write_file" in types

    def test_multiple_write_file_blocks(self):
        """Parse multiple write_file blocks."""
        parser = StreamingParser()
        events = parser.feed_and_finalize(
            "<write_file path='/a.py'>a</write_file><write_file path='/b.py'>b</write_file>"
        )
        
        segments = extract_segments(events)
        write_file_segments = [s for s in segments if s["type"] == "write_file"]
        assert len(write_file_segments) >= 2


class TestStreamingParserStateManagement:
    """Tests for parser state management."""

    def test_cannot_feed_after_finalize(self):
        """Feeding after finalize raises error."""
        parser = StreamingParser()
        parser.feed("test")
        parser.finalize()
        
        with pytest.raises(RuntimeError, match="Cannot feed"):
            parser.feed("more")

    def test_cannot_finalize_twice(self):
        """Finalizing twice raises error."""
        parser = StreamingParser()
        parser.finalize()
        
        with pytest.raises(RuntimeError, match="already been called"):
            parser.finalize()

    def test_is_finalized_property(self):
        """is_finalized property works correctly."""
        parser = StreamingParser()
        assert parser.is_finalized is False
        
        parser.finalize()
        assert parser.is_finalized is True


class TestConvenienceFunctions:
    """Tests for convenience functions."""

    def test_parse_complete_response(self):
        """parse_complete_response function works."""
        events = parse_complete_response("Hello World!")
        
        assert len(events) > 0
        segments = extract_segments(events)
        assert len(segments) >= 1

    def test_extract_segments_basic(self):
        """extract_segments correctly builds segment list."""
        parser = StreamingParser()
        events = parser.feed_and_finalize("Plain text here")
        
        segments = extract_segments(events)
        
        assert len(segments) >= 1
        assert segments[0]["type"] == "text"
        assert "Plain text here" in segments[0]["content"]


class TestStreamingParserStreaming:
    """Tests simulating real streaming scenarios."""

    def test_chunk_by_chunk_streaming(self):
        """Simulate chunk-by-chunk LLM streaming."""
        parser = StreamingParser()
        
        all_events = []
        
        # Simulate streaming chunks
        chunks = ["He", "llo, ", "I can ", "help you!"]
        for chunk in chunks:
            events = parser.feed(chunk)
            all_events.extend(events)
        
        final_events = parser.finalize()
        all_events.extend(final_events)
        
        # Should produce text segments
        segments = extract_segments(all_events)
        combined_text = "".join(s["content"] for s in segments if s["type"] == "text")
        assert "Hello, I can help you!" in combined_text

    def test_write_file_split_across_chunks(self):
        """Write_file tag content split across chunks."""
        parser = StreamingParser()
        
        all_events = []
        
        chunks = ["<wri", "te_file path='/test.py'>print", "('hello')</write_file>"]
        for chunk in chunks:
            events = parser.feed(chunk)
            all_events.extend(events)
        
        final_events = parser.finalize()
        all_events.extend(final_events)
        
        segments = extract_segments(all_events)
        write_file_segments = [s for s in segments if s["type"] == "write_file"]
        assert len(write_file_segments) >= 1
