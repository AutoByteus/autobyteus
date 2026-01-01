"""
Unit tests for the StreamScanner class.
"""
import pytest
from autobyteus.agent.streaming.parser.stream_scanner import StreamScanner


class TestStreamScannerBasics:
    """Tests for basic StreamScanner operations."""

    def test_initial_empty_buffer(self):
        """Scanner starts with empty buffer and position 0."""
        scanner = StreamScanner()
        assert scanner.get_position() == 0
        assert scanner.get_buffer_length() == 0
        assert scanner.has_more_chars() is False
        assert scanner.peek() is None

    def test_initial_with_buffer(self):
        """Scanner can be initialized with a buffer."""
        scanner = StreamScanner("hello")
        assert scanner.get_position() == 0
        assert scanner.get_buffer_length() == 5
        assert scanner.has_more_chars() is True
        assert scanner.peek() == "h"


class TestStreamScannerAppend:
    """Tests for append functionality."""

    def test_append_to_empty(self):
        """Appending to empty buffer works."""
        scanner = StreamScanner()
        scanner.append("abc")
        assert scanner.get_buffer_length() == 3
        assert scanner.peek() == "a"

    def test_append_multiple_times(self):
        """Multiple appends accumulate correctly."""
        scanner = StreamScanner("he")
        scanner.append("llo")
        scanner.append(" world")
        assert scanner.get_buffer_length() == 11
        assert scanner.substring(0) == "hello world"


class TestStreamScannerNavigation:
    """Tests for cursor navigation."""

    def test_advance_single(self):
        """Advance moves cursor by one."""
        scanner = StreamScanner("abc")
        assert scanner.peek() == "a"
        scanner.advance()
        assert scanner.peek() == "b"
        assert scanner.get_position() == 1

    def test_advance_at_end(self):
        """Advance at end of buffer is safe (no-op)."""
        scanner = StreamScanner("a")
        scanner.advance()  # Now at end
        assert scanner.has_more_chars() is False
        scanner.advance()  # Should not crash
        assert scanner.get_position() == 1

    def test_advance_by(self):
        """Advance by multiple positions."""
        scanner = StreamScanner("hello world")
        scanner.advance_by(6)
        assert scanner.peek() == "w"
        assert scanner.get_position() == 6

    def test_advance_by_past_end(self):
        """Advance by past end clamps to buffer length."""
        scanner = StreamScanner("abc")
        scanner.advance_by(100)
        assert scanner.get_position() == 3
        assert scanner.has_more_chars() is False


class TestStreamScannerSubstring:
    """Tests for substring extraction."""

    def test_substring_full(self):
        """Substring with only start returns to end."""
        scanner = StreamScanner("hello world")
        assert scanner.substring(6) == "world"

    def test_substring_range(self):
        """Substring with start and end."""
        scanner = StreamScanner("hello world")
        assert scanner.substring(0, 5) == "hello"

    def test_substring_empty(self):
        """Substring with same start and end returns empty."""
        scanner = StreamScanner("hello")
        assert scanner.substring(2, 2) == ""


class TestStreamScannerSetPosition:
    """Tests for set_position functionality."""

    def test_set_position_valid(self):
        """Set position to valid index."""
        scanner = StreamScanner("hello")
        scanner.set_position(3)
        assert scanner.get_position() == 3
        assert scanner.peek() == "l"

    def test_set_position_negative(self):
        """Set position to negative clamps to 0."""
        scanner = StreamScanner("hello")
        scanner.set_position(-5)
        assert scanner.get_position() == 0

    def test_set_position_past_end(self):
        """Set position past end clamps to buffer length."""
        scanner = StreamScanner("hello")
        scanner.set_position(100)
        assert scanner.get_position() == 5


class TestStreamScannerIntegration:
    """Integration tests simulating streaming parser usage."""

    def test_streaming_append_pattern(self):
        """Simulate receiving chunks while parsing."""
        scanner = StreamScanner()
        
        # First chunk arrives
        scanner.append("<to")
        assert scanner.peek() == "<"
        scanner.advance()
        assert scanner.peek() == "t"
        scanner.advance()
        assert scanner.peek() == "o"
        scanner.advance()
        assert scanner.has_more_chars() is False
        
        # Second chunk arrives
        scanner.append("ol>")
        assert scanner.has_more_chars() is True
        assert scanner.peek() == "o"

    def test_rewind_pattern(self):
        """Simulate rewinding cursor for re-parsing."""
        scanner = StreamScanner("<tool name='test'>")
        
        # Advance through tag
        scanner.advance_by(5)  # Past "<tool"
        assert scanner.peek() == " "
        
        # Rewind to start of tag
        scanner.set_position(0)
        assert scanner.peek() == "<"
        
        # Extract the full tag
        result = scanner.substring(0, 18)
        assert result == "<tool name='test'>"
