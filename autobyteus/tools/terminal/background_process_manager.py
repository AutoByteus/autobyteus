"""
Background Process Manager for long-running processes.

Manages multiple PTY sessions for background processes like servers,
with output buffering and lifecycle management.
"""

from __future__ import annotations

import asyncio
import logging
import time
import uuid
from typing import Callable, Dict, Optional

from autobyteus.tools.terminal.output_buffer import OutputBuffer
from autobyteus.tools.terminal.session_factory import get_default_session_factory
from autobyteus.tools.terminal.types import BackgroundProcessOutput, ProcessInfo
from autobyteus.tools.terminal.ansi_utils import strip_ansi_codes

logger = logging.getLogger(__name__)


class BackgroundProcess:
    """Wrapper for a background process with its PTY and output buffer."""
    
    def __init__(
        self,
        process_id: str,
        command: str,
        session: object,
        output_buffer: OutputBuffer
    ):
        self.process_id = process_id
        self.command = command
        self.session = session
        self.output_buffer = output_buffer
        self.started_at = time.time()
        self._reader_task: Optional[asyncio.Task] = None
    
    @property
    def is_running(self) -> bool:
        return self.session.is_alive
    
    def to_info(self) -> ProcessInfo:
        return ProcessInfo(
            process_id=self.process_id,
            command=self.command,
            started_at=self.started_at,
            is_running=self.is_running
        )


class BackgroundProcessManager:
    """Manages background processes (servers, watchers, etc.).
    
    Each background process runs in its own PTY session with
    continuous output buffering.
    """
    
    def __init__(
        self,
        session_factory: Callable[[str], object] = None,
        max_output_bytes: int = 1_000_000
    ):
        """Initialize the background process manager.
        
        Args:
            session_factory: Factory function to create PtySession instances.
            max_output_bytes: Maximum bytes to buffer per process.
        """
        self._session_factory = session_factory or get_default_session_factory()
        self._max_output_bytes = max_output_bytes
        self._processes: Dict[str, BackgroundProcess] = {}
        self._counter = 0
    
    def _generate_id(self) -> str:
        """Generate a unique process ID."""
        self._counter += 1
        return f"bg_{self._counter:03d}"
    
    async def start_process(self, command: str, cwd: str) -> str:
        """Start a long-running process in the background.
        
        Args:
            command: The command to run.
            cwd: Working directory for the process.
            
        Returns:
            Process ID that can be used to reference this process.
        """
        process_id = self._generate_id()
        session_id = f"bg-{uuid.uuid4().hex[:8]}"
        
        session = self._session_factory(session_id)
        output_buffer = OutputBuffer(max_bytes=self._max_output_bytes)
        
        # Start the session
        await session.start(cwd)
        
        # Create process wrapper
        bg_process = BackgroundProcess(
            process_id=process_id,
            command=command,
            session=session,
            output_buffer=output_buffer
        )
        
        # Write the command
        if not command.endswith('\n'):
            command += '\n'
        await session.write(command.encode('utf-8'))
        
        # Start background reader task
        bg_process._reader_task = asyncio.create_task(
            self._read_loop(bg_process)
        )
        
        self._processes[process_id] = bg_process
        logger.info(f"Started background process {process_id}: {command.strip()}")
        
        return process_id
    
    async def _read_loop(self, process: BackgroundProcess) -> None:
        """Background task that continuously reads output from the PTY.
        
        Args:
            process: The background process to read from.
        """
        try:
            while process.session.is_alive:
                try:
                    data = await process.session.read(timeout=0.1)
                    if data:
                        process.output_buffer.append(data)
                except Exception as e:
                    logger.debug(f"Read error for {process.process_id}: {e}")
                    break
                
                await asyncio.sleep(0.05)
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Error in read loop for {process.process_id}: {e}")
    
    def get_output(
        self,
        process_id: str,
        lines: int = 100
    ) -> BackgroundProcessOutput:
        """Get recent output from a background process.
        
        Args:
            process_id: ID of the process.
            lines: Number of recent lines to return.
            
        Returns:
            BackgroundProcessOutput with output and status.
            
        Raises:
            KeyError: If process_id not found.
        """
        if process_id not in self._processes:
            raise KeyError(f"Process {process_id} not found")
        
        process = self._processes[process_id]
        raw_output = process.output_buffer.get_lines(lines)
        clean_output = strip_ansi_codes(raw_output)
        return BackgroundProcessOutput(
            output=clean_output,
            is_running=process.is_running,
            process_id=process_id
        )
    
    async def stop_process(self, process_id: str) -> bool:
        """Stop a background process.
        
        Sends SIGTERM, then SIGKILL if necessary.
        
        Args:
            process_id: ID of the process to stop.
            
        Returns:
            True if process was found and stopped, False if not found.
        """
        if process_id not in self._processes:
            return False
        
        process = self._processes.pop(process_id)
        
        # Cancel reader task
        if process._reader_task:
            process._reader_task.cancel()
            try:
                await process._reader_task
            except asyncio.CancelledError:
                pass
        
        # Close the PTY session
        await process.session.close()
        
        logger.info(f"Stopped background process {process_id}")
        return True
    
    async def stop_all(self) -> int:
        """Stop all background processes.
        
        Returns:
            Number of processes stopped.
        """
        count = len(self._processes)
        process_ids = list(self._processes.keys())
        
        for process_id in process_ids:
            await self.stop_process(process_id)
        
        return count
    
    def list_processes(self) -> Dict[str, ProcessInfo]:
        """List all background processes.
        
        Returns:
            Dict mapping process_id to ProcessInfo.
        """
        return {
            pid: proc.to_info()
            for pid, proc in self._processes.items()
        }
    
    @property
    def process_count(self) -> int:
        """Number of managed processes."""
        return len(self._processes)
