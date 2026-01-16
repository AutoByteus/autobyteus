"""
PTY Session wrapper for stateful terminal sessions.

This module provides a pseudo-terminal (PTY) abstraction that spawns
a persistent bash shell, enabling stateful terminal operations where
directory changes, environment variables, and shell state persist
across commands.
"""

import asyncio
import fcntl
import logging
import os
import pty
import select
import signal
import struct
import termios
from typing import Optional

logger = logging.getLogger(__name__)


class PtySession:
    """PTY session implementation using the pty module.
    
    Spawns a persistent bash shell that maintains state across commands.
    
    For testing, create a MockPtySession with the same interface (duck typing).
    
    Attributes:
        session_id: Unique identifier for this session.
    """
    
    def __init__(self, session_id: str):
        """Initialize a PTY session.
        
        Args:
            session_id: Unique identifier for this session.
        """
        self._session_id = session_id
        self._master_fd: Optional[int] = None
        self._pid: Optional[int] = None
        self._closed = False
        self._cwd: Optional[str] = None
    
    @property
    def session_id(self) -> str:
        """Unique session identifier."""
        return self._session_id
    
    @property
    def is_alive(self) -> bool:
        """Check if the shell process is still running."""
        if self._pid is None or self._closed:
            return False
        try:
            # Check if process exists without waiting
            pid, status = os.waitpid(self._pid, os.WNOHANG)
            if pid == 0:
                return True  # Process still running
            return False  # Process exited
        except ChildProcessError:
            return False
    
    async def start(self, cwd: str) -> None:
        """Start a bash shell in a PTY.
        
        Uses fork/exec to create a child process with a pseudo-terminal.
        
        Args:
            cwd: Working directory for the shell.
            
        Raises:
            RuntimeError: If session is already started.
            OSError: If fork or PTY creation fails.
        """
        if self._master_fd is not None:
            raise RuntimeError("Session already started")
        
        self._cwd = cwd
        
        # Create pseudo-terminal
        master_fd, slave_fd = pty.openpty()
        
        pid = os.fork()
        
        if pid == 0:
            # Child process
            try:
                os.close(master_fd)
                os.setsid()
                
                # Make slave the controlling terminal
                fcntl.ioctl(slave_fd, termios.TIOCSCTTY, 0)
                
                # Redirect stdin/stdout/stderr to slave
                os.dup2(slave_fd, 0)
                os.dup2(slave_fd, 1)
                os.dup2(slave_fd, 2)
                
                if slave_fd > 2:
                    os.close(slave_fd)
                
                # Set environment variables for minimal output
                os.environ['TERM'] = 'dumb'
                # Simple prompt for easier detection
                os.environ['PS1'] = '$ '
                
                # Change to working directory
                os.chdir(cwd)
                
                # Execute bash with minimal startup (non-interactive)
                os.execlp('bash', 'bash', '--norc', '--noprofile')
            except Exception as e:
                logger.error(f"Child process error: {e}")
                os._exit(1)
        else:
            # Parent process
            os.close(slave_fd)
            self._master_fd = master_fd
            self._pid = pid
            
            # Set non-blocking mode
            flags = fcntl.fcntl(master_fd, fcntl.F_GETFL)
            fcntl.fcntl(master_fd, fcntl.F_SETFL, flags | os.O_NONBLOCK)
            
            # Give bash a moment to start
            await asyncio.sleep(0.1)
            
            logger.info(f"Started PTY session {self._session_id} (pid={pid}) in {cwd}")
    
    async def write(self, data: bytes) -> None:
        """Write data to the PTY master.
        
        Args:
            data: Bytes to write to the terminal.
            
        Raises:
            RuntimeError: If session is closed or not started.
        """
        if self._closed:
            raise RuntimeError("Session is closed")
        if self._master_fd is None:
            raise RuntimeError("Session not started")
        
        try:
            os.write(self._master_fd, data)
        except OSError as e:
            logger.error(f"Error writing to PTY: {e}")
            raise
    
    async def read(self, timeout: float = 0.1) -> Optional[bytes]:
        """Read available data from the PTY.
        
        Uses select for non-blocking read with timeout.
        
        Args:
            timeout: Maximum time to wait for data in seconds.
            
        Returns:
            Bytes read from PTY, or None if no data available.
            
        Raises:
            RuntimeError: If session not started.
        """
        if self._closed:
            return None
        if self._master_fd is None:
            raise RuntimeError("Session not started")
        
        try:
            # Wait for data with timeout
            readable, _, _ = select.select([self._master_fd], [], [], timeout)
            
            if not readable:
                return None
            
            # Read available data
            data = os.read(self._master_fd, 4096)
            return data if data else None
            
        except OSError as e:
            if e.errno == 5:  # EIO - terminal closed
                return None
            logger.error(f"Error reading from PTY: {e}")
            raise
    
    def resize(self, rows: int, cols: int) -> None:
        """Resize the PTY terminal.
        
        Args:
            rows: Number of rows.
            cols: Number of columns.
        """
        if self._master_fd is None:
            raise RuntimeError("Session not started")
        if self._closed:
            return
        
        try:
            winsize = struct.pack('HHHH', rows, cols, 0, 0)
            fcntl.ioctl(self._master_fd, termios.TIOCSWINSZ, winsize)
            logger.debug(f"Resized PTY {self._session_id} to {rows}x{cols}")
        except OSError as e:
            logger.error(f"Error resizing PTY: {e}")
    
    async def close(self) -> None:
        """Close the PTY and terminate the shell.
        
        Sends SIGTERM first, then SIGKILL if necessary.
        """
        if self._closed:
            return
        
        self._closed = True
        
        if self._master_fd is not None:
            try:
                os.close(self._master_fd)
            except OSError:
                pass
            self._master_fd = None
        
        if self._pid is not None:
            try:
                # Try graceful termination first
                os.kill(self._pid, signal.SIGTERM)
                # Wait briefly
                await asyncio.sleep(0.1)
                # Force kill if still running
                try:
                    os.kill(self._pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass  # Already dead
                os.waitpid(self._pid, 0)
            except (ProcessLookupError, ChildProcessError):
                pass
            self._pid = None
        
        logger.info(f"Closed PTY session {self._session_id}")
