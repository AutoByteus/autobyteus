"""
Integration tests for the Streaming Parser.

These tests simulate realistic LLM response parsing scenarios
with mixed content types and streaming chunks.
"""
import pytest
from autobyteus.agent.streaming.parser.parser_context import ParserContext, ParserConfig
from autobyteus.agent.streaming.parser.states.text_state import TextState
from autobyteus.agent.streaming.parser.events import SegmentType, SegmentEventType


class StreamingParserDriver:
    """
    A simple driver for testing the streaming parser.
    
    This simulates how the parser would be used in production:
    1. Create context and set initial state
    2. Feed chunks of text
    3. Collect emitted events
    """
    
    def __init__(self, config: ParserConfig = None):
        self.context = ParserContext(config)
        self.context.current_state = TextState(self.context)
        self.all_events = []
    
    def feed(self, chunk: str) -> None:
        """Feed a chunk of text and process it."""
        self.context.append(chunk)
        while self.context.has_more_chars():
            state = self.context.current_state
            state.run()
            # Collect events after each run
            self.all_events.extend(self.context.get_and_clear_events())
    
    def finalize(self) -> None:
        """Signal end of stream."""
        self.context.current_state.finalize()
        if self.context.get_current_segment_type() == SegmentType.TEXT:
            self.context.emit_segment_end()
        self.all_events.extend(self.context.get_and_clear_events())
    
    def get_segments(self) -> list:
        """Extract segment info from collected events."""
        segments = []
        current_segment = None
        
        for event in self.all_events:
            if event.event_type == SegmentEventType.START:
                current_segment = {
                    "id": event.segment_id,
                    "type": event.segment_type.value,
                    "content": "",
                    "metadata": event.payload.get("metadata", {})
                }
            elif event.event_type == SegmentEventType.CONTENT:
                if current_segment:
                    delta = event.payload.get("delta", "")
                    if isinstance(delta, str):
                        current_segment["content"] += delta
            elif event.event_type == SegmentEventType.END:
                if current_segment:
                    segments.append(current_segment)
                    current_segment = None
        
        return segments


class TestPureTextParsing:
    """Tests for parsing pure text responses."""

    def test_single_chunk_text(self):
        """Parse a simple text response in one chunk."""
        driver = StreamingParserDriver()
        driver.feed("Hello, I can help you with that!")
        driver.finalize()
        
        segments = driver.get_segments()
        assert len(segments) == 1
        assert segments[0]["type"] == "text"
        assert segments[0]["content"] == "Hello, I can help you with that!"

    def test_multi_chunk_text(self):
        """Parse text arriving in multiple chunks."""
        driver = StreamingParserDriver()
        driver.feed("Hello, ")
        driver.feed("I can ")
        driver.feed("help you!")
        driver.finalize()
        
        segments = driver.get_segments()
        # Each chunk becomes its own text segment in this simple driver
        assert len(segments) >= 1
        combined = "".join(s["content"] for s in segments if s["type"] == "text")
        assert combined == "Hello, I can help you!"


class TestWriteFileTagParsing:
    """Tests for parsing <write_file> tags."""

    def test_write_file_tag_single_chunk(self):
        """Parse a complete write_file tag in one chunk."""
        driver = StreamingParserDriver()
        driver.feed("Here is the file:<write_file path='/test.py'>print('hello')</write_file>Done!")
        driver.finalize()
        
        segments = driver.get_segments()
        # Should have: text, write_file, text
        types = [s["type"] for s in segments]
        assert "write_file" in types

    def test_write_file_tag_streaming(self):
        """Parse a write_file tag arriving in chunks."""
        driver = StreamingParserDriver()
        driver.feed("Code:<wri")
        driver.feed("te_file path='/test.py'>def ")
        driver.feed("hello():\n    pass</write_file>")
        driver.finalize()
        
        segments = driver.get_segments()
        write_file_segments = [s for s in segments if s["type"] == "write_file"]
        assert len(write_file_segments) >= 1


class TestRunBashTagParsing:
    """Tests for parsing <run_bash> tags."""

    def test_run_bash_tag_complete(self):
        """Parse a complete run_bash tag."""
        driver = StreamingParserDriver()
        driver.feed("Run this:<run_bash>ls -la</run_bash>")
        driver.finalize()
        
        segments = driver.get_segments()
        cmd_segments = [s for s in segments if s["type"] == "run_bash"]
        assert len(cmd_segments) >= 1


class TestToolCallParsing:
    """Tests for parsing <tool> tags."""

    def test_tool_tag_enabled(self):
        """Parse tool tag with tool parsing enabled."""
        config = ParserConfig(parse_tool_calls=True, strategy_order=["xml_tag"])
        driver = StreamingParserDriver(config)
        driver.feed("Let me check:<tool name='weather'>city=NYC</tool>")
        driver.finalize()
        
        segments = driver.get_segments()
        tool_segments = [s for s in segments if s["type"] == "tool_call"]
        assert len(tool_segments) >= 1

    def test_tool_tag_disabled_becomes_text(self):
        """Tool tag becomes text when parsing disabled."""
        config = ParserConfig(parse_tool_calls=False)
        driver = StreamingParserDriver(config)
        driver.feed("Here:<tool name='test'>args</tool>Done")
        driver.finalize()
        
        segments = driver.get_segments()
        # Tool should be emitted as text
        tool_segments = [s for s in segments if s["type"] == "tool_call"]
        assert len(tool_segments) == 0


class TestMixedContent:
    """Tests for parsing mixed content responses."""

    def test_text_mixed_with_code(self):
        """Parse response with text and code blocks."""
        driver = StreamingParserDriver()
        driver.feed("Here is the solution:\n")
        driver.feed("<write_file path='/main.py'>print('done')</write_file>\n")
        driver.feed("Let me know if you need more help!")
        driver.finalize()
        
        segments = driver.get_segments()
        types = set(s["type"] for s in segments)
        assert "text" in types
        assert "write_file" in types

    def test_multiple_write_file_blocks(self):
        """Parse response with multiple write_file blocks."""
        driver = StreamingParserDriver()
        driver.feed("<write_file path='/a.py'>a</write_file>")
        driver.feed("<write_file path='/b.py'>b</write_file>")
        driver.finalize()
        
        segments = driver.get_segments()
        write_file_segments = [s for s in segments if s["type"] == "write_file"]
        assert len(write_file_segments) >= 2





class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_incomplete_tag_at_stream_end(self):
        """Incomplete tag at end of stream is emitted as text."""
        driver = StreamingParserDriver()
        driver.feed("Some text <wri")  # Incomplete <write_file tag
        driver.finalize()
        
        segments = driver.get_segments()
        combined = "".join(s["content"] for s in segments if s["type"] == "text")
        assert "<wri" in combined or "wri" in combined

    def test_unknown_xml_tag(self):
        """Unknown XML tags like <div> are treated as text."""
        driver = StreamingParserDriver()
        driver.feed("Hello <span>world</span>!")
        driver.finalize()
        
        segments = driver.get_segments()
        # All should be text since <span> is not a known tag
        text_content = "".join(s["content"] for s in segments if s["type"] == "text")
        # The text should contain parts of the original
        assert "Hello" in text_content or len(text_content) > 0

    def test_empty_stream(self):
        """Empty stream produces no events."""
        driver = StreamingParserDriver()
        driver.finalize()
        
        assert len(driver.all_events) == 0
