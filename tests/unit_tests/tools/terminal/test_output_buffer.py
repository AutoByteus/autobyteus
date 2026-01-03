"""
Unit tests for output_buffer.py
"""

import pytest
from autobyteus.tools.terminal.output_buffer import OutputBuffer


class TestOutputBuffer:
    """Tests for OutputBuffer class."""
    
    def test_append_and_get_all(self):
        """Test basic append and retrieval."""
        buffer = OutputBuffer()
        buffer.append(b"Hello\n")
        buffer.append(b"World\n")
        
        result = buffer.get_all()
        assert result == "Hello\nWorld\n"
    
    def test_append_empty_data(self):
        """Test appending empty data does nothing."""
        buffer = OutputBuffer()
        buffer.append(b"")
        buffer.append(b"test\n")
        
        assert buffer.get_all() == "test\n"
    
    def test_get_lines_returns_last_n(self):
        """Test get_lines returns last n lines."""
        buffer = OutputBuffer()
        for i in range(10):
            buffer.append(f"line {i}\n".encode())
        
        result = buffer.get_lines(3)
        assert "line 7\n" in result
        assert "line 8\n" in result
        assert "line 9\n" in result
        assert "line 0\n" not in result
    
    def test_get_lines_more_than_available(self):
        """Test get_lines when requesting more lines than exist."""
        buffer = OutputBuffer()
        buffer.append(b"line 1\n")
        buffer.append(b"line 2\n")
        
        result = buffer.get_lines(100)
        assert result == "line 1\nline 2\n"
    
    def test_clear(self):
        """Test clear removes all content."""
        buffer = OutputBuffer()
        buffer.append(b"test content\n")
        assert buffer.size > 0
        
        buffer.clear()
        assert buffer.size == 0
        assert buffer.get_all() == ""
    
    def test_size_property(self):
        """Test size property returns correct byte count."""
        buffer = OutputBuffer()
        buffer.append(b"hello")  # 5 bytes
        
        assert buffer.size == 5
    
    def test_line_count_property(self):
        """Test line_count returns number of lines."""
        buffer = OutputBuffer()
        buffer.append(b"line 1\n")
        buffer.append(b"line 2\n")
        buffer.append(b"line 3\n")
        
        assert buffer.line_count == 3
    
    def test_max_bytes_limit(self):
        """Test buffer respects max_bytes limit by discarding old data."""
        buffer = OutputBuffer(max_bytes=50)
        
        # Add more than 50 bytes
        for i in range(20):
            buffer.append(f"line {i:02d}\n".encode())  # ~9 bytes each
        
        # Should have discarded old lines
        assert buffer.size <= 50
        # Latest lines should still be present
        assert "line 19\n" in buffer.get_all()
    
    def test_unicode_handling(self):
        """Test buffer handles unicode correctly."""
        buffer = OutputBuffer()
        buffer.append("Hello 世界\n".encode('utf-8'))
        
        result = buffer.get_all()
        assert "世界" in result
    
    def test_invalid_utf8_handling(self):
        """Test buffer handles invalid UTF-8 gracefully."""
        buffer = OutputBuffer()
        # Invalid UTF-8 sequence
        buffer.append(b"\xff\xfe invalid")
        
        # Should not raise, should use replacement characters
        result = buffer.get_all()
        assert len(result) > 0


class TestOutputBufferThreadSafety:
    """Tests for thread safety of OutputBuffer."""
    
    def test_concurrent_appends(self):
        """Test concurrent appends don't corrupt data."""
        import threading
        
        buffer = OutputBuffer()
        threads = []
        
        def append_lines(prefix: str, count: int):
            for i in range(count):
                buffer.append(f"{prefix}-{i}\n".encode())
        
        for i in range(5):
            t = threading.Thread(target=append_lines, args=(f"thread{i}", 100))
            threads.append(t)
        
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        # All 500 lines should be present (though order may vary)
        assert buffer.line_count == 500
