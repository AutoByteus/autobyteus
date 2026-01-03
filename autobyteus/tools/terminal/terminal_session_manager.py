"""
Terminal Session Manager for executing commands in a stateful PTY.

Provides high-level command execution with prompt detection and
timeout handling.
"""

import asyncio
import logging
import uuid
from typing import Callable, Optional

from autobyteus.tools.terminal.output_buffer import OutputBuffer
from autobyteus.tools.terminal.prompt_detector import PromptDetector
from autobyteus.tools.terminal.pty_session import PtySession
from autobyteus.tools.terminal.types import TerminalResult

logger = logging.getLogger(__name__)


class TerminalSessionManager:
    """Manages the main stateful terminal session for an agent.
    
    Provides command execution with automatic prompt detection and
    timeout handling. The underlying PTY maintains state between
    commands (cd, environment variables, etc).
    
    Attributes:
        current_session: The active PTY session if started.
    """
    
    def __init__(
        self,
        session_factory: Callable[[str], PtySession] = None,
        prompt_detector: PromptDetector = None
    ):
        """Initialize the terminal session manager.
        
        Args:
            session_factory: Factory function to create PtySession instances.
                           Defaults to PtySession constructor.
            prompt_detector: PromptDetector instance for command completion.
                           Defaults to standard PromptDetector.
        """
        self._session_factory = session_factory or PtySession
        self._prompt_detector = prompt_detector or PromptDetector()
        self._session: Optional[PtySession] = None
        self._output_buffer = OutputBuffer()
        self._cwd: Optional[str] = None
        self._started = False
    
    @property
    def current_session(self) -> Optional[PtySession]:
        """The active PTY session if started."""
        return self._session
    
    @property
    def is_started(self) -> bool:
        """True if session has been started."""
        return self._started and self._session is not None
    
    async def ensure_started(self, cwd: str) -> None:
        """Ensure the session is started.
        
        Creates a new session if not already started.
        
        Args:
            cwd: Working directory for the shell.
        """
        if self._session is not None and self._session.is_alive:
            return
        
        # Clean up dead session if any
        if self._session is not None:
            await self._session.close()
        
        session_id = f"term-{uuid.uuid4().hex[:8]}"
        self._session = self._session_factory(session_id)
        await self._session.start(cwd)
        self._cwd = cwd
        self._started = True
        
        # Drain initial prompt output
        await self._drain_output(timeout=0.5)
        self._output_buffer.clear()
        
        logger.info(f"Terminal session started in {cwd}")
    
    async def execute_command(
        self,
        command: str,
        timeout_seconds: int = 30
    ) -> TerminalResult:
        """Execute a command and wait for completion.
        
        Writes the command to the PTY and waits for the prompt to
        return, indicating command completion.
        
        Args:
            command: The bash command to execute.
            timeout_seconds: Maximum time to wait for completion.
            
        Returns:
            TerminalResult with captured output.
            
        Raises:
            RuntimeError: If session is not started.
        """
        if self._session is None:
            raise RuntimeError("Session not started. Call ensure_started first.")
        
        # Clear buffer for this command
        self._output_buffer.clear()
        
        # Ensure command ends with newline
        if not command.endswith('\n'):
            command += '\n'
        
        # Write command
        await self._session.write(command.encode('utf-8'))
        
        # Wait for prompt with timeout
        timed_out = False
        start_time = asyncio.get_event_loop().time()
        
        while True:
            elapsed = asyncio.get_event_loop().time() - start_time
            if elapsed >= timeout_seconds:
                timed_out = True
                logger.warning(f"Command timed out after {timeout_seconds}s: {command.strip()}")
                break
            
            # Read available output
            try:
                data = await self._session.read(timeout=0.1)
                if data:
                    self._output_buffer.append(data)
                    
                    # Check if prompt returned
                    current_output = self._output_buffer.get_all()
                    if self._prompt_detector.check(current_output):
                        break
            except Exception as e:
                logger.error(f"Error reading from PTY: {e}")
                break
        
        # Get captured output
        output = self._output_buffer.get_all()
        
        # Try to extract exit code if not timed out
        exit_code = None
        if not timed_out:
            exit_code = await self._get_exit_code()
        
        return TerminalResult(
            stdout=output,
            stderr="",  # PTY mixes stdout/stderr
            exit_code=exit_code,
            timed_out=timed_out
        )
    
    async def _get_exit_code(self) -> Optional[int]:
        """Try to get the exit code of the last command.
        
        Returns:
            Exit code if successfully retrieved, None otherwise.
        """
        try:
            # Clear buffer
            self._output_buffer.clear()
            
            # Echo the exit code
            await self._session.write(b"echo $?\n")
            
            # Wait for output
            await asyncio.sleep(0.2)
            await self._drain_output(timeout=0.3)
            
            output = self._output_buffer.get_all()
            
            # Parse the exit code from output
            lines = output.strip().split('\n')
            for line in lines:
                line = line.strip()
                if line.isdigit():
                    return int(line)
            
            return None
        except Exception as e:
            logger.debug(f"Failed to get exit code: {e}")
            return None
    
    async def _drain_output(self, timeout: float = 0.5) -> None:
        """Read and buffer all available output.
        
        Args:
            timeout: Maximum time to wait for more output.
        """
        if self._session is None:
            return
            
        start = asyncio.get_event_loop().time()
        while asyncio.get_event_loop().time() - start < timeout:
            try:
                data = await self._session.read(timeout=0.05)
                if data:
                    self._output_buffer.append(data)
                else:
                    # No more data immediately available
                    await asyncio.sleep(0.05)
            except Exception:
                break
    
    async def close(self) -> None:
        """Close the terminal session."""
        if self._session is not None:
            await self._session.close()
            self._session = None
        self._started = False
        self._output_buffer.clear()
        logger.info("Terminal session closed")
