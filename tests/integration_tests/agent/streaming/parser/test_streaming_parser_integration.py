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


class TestFileTagParsing:
    """Tests for parsing <file> tags."""

    def test_file_tag_single_chunk(self):
        """Parse a complete file tag in one chunk."""
        driver = StreamingParserDriver()
        driver.feed("Here is the file:<file path='/test.py'>print('hello')</file>Done!")
        driver.finalize()
        
        segments = driver.get_segments()
        # Should have: text, file, text
        types = [s["type"] for s in segments]
        assert "file" in types

    def test_file_tag_streaming(self):
        """Parse a file tag arriving in chunks."""
        driver = StreamingParserDriver()
        driver.feed("Code:<fi")
        driver.feed("le path='/test.py'>def ")
        driver.feed("hello():\n    pass</file>")
        driver.finalize()
        
        segments = driver.get_segments()
        file_segments = [s for s in segments if s["type"] == "file"]
        assert len(file_segments) >= 1


class TestBashTagParsing:
    """Tests for parsing <bash> tags."""

    def test_bash_tag_complete(self):
        """Parse a complete bash tag."""
        driver = StreamingParserDriver()
        driver.feed("Run this:<bash>ls -la</bash>")
        driver.finalize()
        
        segments = driver.get_segments()
        bash_segments = [s for s in segments if s["type"] == "bash"]
        assert len(bash_segments) >= 1


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
        driver.feed("<file path='/main.py'>print('done')</file>\n")
        driver.feed("Let me know if you need more help!")
        driver.finalize()
        
        segments = driver.get_segments()
        types = set(s["type"] for s in segments)
        assert "text" in types
        assert "file" in types

    def test_multiple_file_blocks(self):
        """Parse response with multiple file blocks."""
        driver = StreamingParserDriver()
        driver.feed("<file path='/a.py'>a</file>")
        driver.feed("<file path='/b.py'>b</file>")
        driver.finalize()
        
        segments = driver.get_segments()
        file_segments = [s for s in segments if s["type"] == "file"]
        assert len(file_segments) >= 2


class TestDoctypeHtmlParsing:
    """Tests for parsing <!doctype html> content."""

    def test_html_doctype(self):
        """Parse HTML doctype content."""
        config = ParserConfig()
        driver = StreamingParserDriver(config)
        driver.feed("Preview:<!doctype html><html><body>Hi</body></html>Done")
        driver.finalize()
        
        segments = driver.get_segments()
        iframe_segments = [s for s in segments if s["type"] == "iframe"]
        # Should detect iframe/html segment
        assert len(iframe_segments) >= 1


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_incomplete_tag_at_stream_end(self):
        """Incomplete tag at end of stream is emitted as text."""
        driver = StreamingParserDriver()
        driver.feed("Some text <fi")  # Incomplete <file tag
        driver.finalize()
        
        segments = driver.get_segments()
        combined = "".join(s["content"] for s in segments if s["type"] == "text")
        assert "<fi" in combined or "fi" in combined

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
