"""
Ring buffer for capturing terminal output.

Provides bounded memory storage for command output with
support for retrieving recent lines.
"""

import threading
from collections import deque
from typing import List


class OutputBuffer:
    """Ring buffer that stores output with bounded memory.
    
    Thread-safe buffer for capturing terminal output. Stores data
    up to a maximum byte limit, discarding oldest data when full.
    
    Attributes:
        max_bytes: Maximum bytes to store before discarding old data.
    """
    
    def __init__(self, max_bytes: int = 1_000_000):
        """Initialize the output buffer.
        
        Args:
            max_bytes: Maximum bytes to store (default 1MB).
        """
        self._max_bytes = max_bytes
        self._buffer: deque = deque()
        self._total_bytes = 0
        self._lock = threading.Lock()
    
    def append(self, data: bytes) -> None:
        """Append data to the buffer.
        
        If adding data would exceed max_bytes, oldest lines are
        discarded to make room.
        
        Args:
            data: Bytes to append to the buffer.
        """
        if not data:
            return
            
        with self._lock:
            # Decode and split by lines, keeping line endings
            try:
                text = data.decode('utf-8', errors='replace')
            except Exception:
                text = str(data)
            
            # Split into lines but keep partial lines
            lines = text.splitlines(keepends=True)
            
            for line in lines:
                line_bytes = len(line.encode('utf-8'))
                self._buffer.append(line)
                self._total_bytes += line_bytes
            
            # Trim oldest lines if over limit
            while self._total_bytes > self._max_bytes and self._buffer:
                removed = self._buffer.popleft()
                self._total_bytes -= len(removed.encode('utf-8'))
    
    def get_lines(self, n: int = 100) -> str:
        """Get the last n lines from the buffer.
        
        Args:
            n: Number of lines to retrieve.
            
        Returns:
            String containing the last n lines.
        """
        with self._lock:
            if n >= len(self._buffer):
                return ''.join(self._buffer)
            return ''.join(list(self._buffer)[-n:])
    
    def get_all(self) -> str:
        """Get all content from the buffer.
        
        Returns:
            String containing all buffered content.
        """
        with self._lock:
            return ''.join(self._buffer)
    
    def clear(self) -> None:
        """Clear all content from the buffer."""
        with self._lock:
            self._buffer.clear()
            self._total_bytes = 0
    
    @property
    def size(self) -> int:
        """Current size of buffer in bytes."""
        with self._lock:
            return self._total_bytes
    
    @property
    def line_count(self) -> int:
        """Current number of lines in buffer."""
        with self._lock:
            return len(self._buffer)
