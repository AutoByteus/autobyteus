"""
StreamScanner: A class to manage a string buffer and cursor position for sequential reading.

This encapsulates the logic of navigating a stream of text, preventing direct
manipulation of the cursor and buffer from multiple state classes.
"""
from typing import Optional


class StreamScanner:
    """
    Manages a string buffer and a cursor position for sequential reading.
    
    This class encapsulates navigation logic for streaming text, providing
    a clean interface for state machine states to read characters without
    directly manipulating the buffer.
    """
    
    def __init__(self, initial_buffer: str = ""):
        """Initialize the scanner with an optional initial buffer."""
        self._buffer: str = initial_buffer
        self._pos: int = 0

    def append(self, text: str) -> None:
        """Append more text to the end of the buffer."""
        self._buffer += text

    def peek(self) -> Optional[str]:
        """
        Look at the character at the current cursor position without advancing.
        
        Returns:
            The character at the cursor, or None if at the end.
        """
        if self._pos < len(self._buffer):
            return self._buffer[self._pos]
        return None

    def advance(self) -> None:
        """Move the cursor forward by one position."""
        if self.has_more_chars():
            self._pos += 1

    def advance_by(self, count: int) -> None:
        """
        Move the cursor forward by a specified number of positions.
        
        Args:
            count: The number of characters to advance.
        """
        self._pos = min(len(self._buffer), self._pos + count)

    def has_more_chars(self) -> bool:
        """
        Check if there are more characters to read from the buffer.
        
        Returns:
            True if the cursor is not at the end of the buffer.
        """
        return self._pos < len(self._buffer)

    def substring(self, start: int, end: Optional[int] = None) -> str:
        """
        Extract a substring from the buffer.
        
        Args:
            start: The starting index.
            end: The ending index (exclusive). If None, reads to end of buffer.
            
        Returns:
            The extracted substring.
        """
        if end is None:
            return self._buffer[start:]
        return self._buffer[start:end]

    def find(self, sub: str, start: Optional[int] = None) -> int:
        """
        Find a substring in the buffer starting from a position.

        Args:
            sub: The substring to search for.
            start: Optional start index. Defaults to current position.

        Returns:
            The index of the substring, or -1 if not found.
        """
        if start is None:
            start = self._pos
        return self._buffer.find(sub, start)

    def consume(self, count: int) -> str:
        """
        Consume a number of characters from the current position.

        Args:
            count: Number of characters to consume.

        Returns:
            The consumed substring.
        """
        if count <= 0:
            return ""
        end = min(len(self._buffer), self._pos + count)
        result = self._buffer[self._pos:end]
        self._pos = end
        return result

    def consume_remaining(self) -> str:
        """
        Consume all remaining characters in the buffer.

        Returns:
            The remaining substring from current position to end.
        """
        if self._pos >= len(self._buffer):
            return ""
        result = self._buffer[self._pos:]
        self._pos = len(self._buffer)
        return result

    def get_position(self) -> int:
        """
        Return the current zero-based position of the cursor.
        
        Returns:
            The current cursor position.
        """
        return self._pos

    def get_buffer_length(self) -> int:
        """
        Return the total length of the internal buffer.
        
        Returns:
            The length of the buffer.
        """
        return len(self._buffer)

    def set_position(self, position: int) -> None:
        """
        Set the cursor to a specific position.
        
        Args:
            position: The new cursor position (clamped to valid range).
        """
        self._pos = max(0, min(len(self._buffer), position))

    def compact(self, min_prefix: int = 65536) -> None:
        """
        Compact the buffer by dropping consumed prefix data.

        If all data is consumed, clears the buffer entirely.
        Otherwise, drops the consumed prefix when it exceeds min_prefix.

        Args:
            min_prefix: Minimum consumed prefix length to trigger compaction.
        """
        if self._pos == 0:
            return
        if self._pos >= len(self._buffer):
            self._buffer = ""
            self._pos = 0
            return
        if self._pos >= min_prefix:
            self._buffer = self._buffer[self._pos:]
            self._pos = 0
