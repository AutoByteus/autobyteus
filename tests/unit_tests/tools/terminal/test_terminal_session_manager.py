"""
Unit tests for terminal_session_manager.py
"""

import asyncio
import pytest
import tempfile

from autobyteus.tools.terminal.terminal_session_manager import TerminalSessionManager
from autobyteus.tools.terminal.types import TerminalResult


@pytest.fixture
def temp_dir():
    """Create a temporary directory for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


class MockPtySession:
    """Mock PTY session for unit testing."""
    
    def __init__(self, session_id: str):
        self.session_id = session_id
        self._alive = False
        self._output_queue = []
        self._written = []
    
    @property
    def is_alive(self):
        return self._alive
    
    async def start(self, cwd: str):
        self._alive = True
        self._cwd = cwd
        # Simulate initial prompt
        self._output_queue.append(b"$ ")
    
    async def write(self, data: bytes):
        self._written.append(data)
        # Simulate echo and prompt return
        cmd = data.decode().strip()
        if cmd == "echo hello":
            self._output_queue.append(b"echo hello\nhello\n$ ")
        elif cmd == "echo $?":
            self._output_queue.append(b"echo $?\n0\n$ ")
        elif cmd.startswith("sleep"):
            # Long command - don't return prompt immediately
            self._output_queue.append(f"{cmd}\n".encode())
        else:
            self._output_queue.append(f"{cmd}\noutput\n$ ".encode())
    
    async def read(self, timeout: float = 0.1):
        if self._output_queue:
            return self._output_queue.pop(0)
        return None
    
    def resize(self, rows: int, cols: int):
        pass
    
    async def close(self):
        self._alive = False


class TestTerminalSessionManager:
    """Unit tests for TerminalSessionManager."""
    
    @pytest.mark.asyncio
    async def test_ensure_started(self, temp_dir):
        """Test ensure_started creates session."""
        manager = TerminalSessionManager(session_factory=MockPtySession)
        
        assert not manager.is_started
        await manager.ensure_started(temp_dir)
        assert manager.is_started
        
        await manager.close()
    
    @pytest.mark.asyncio
    async def test_ensure_started_idempotent(self, temp_dir):
        """Test ensure_started can be called multiple times."""
        manager = TerminalSessionManager(session_factory=MockPtySession)
        
        await manager.ensure_started(temp_dir)
        session1 = manager.current_session
        
        await manager.ensure_started(temp_dir)
        session2 = manager.current_session
        
        # Should be same session
        assert session1 is session2
        
        await manager.close()
    
    @pytest.mark.asyncio
    async def test_execute_before_start_raises(self):
        """Test execute_command before start raises RuntimeError."""
        manager = TerminalSessionManager(session_factory=MockPtySession)
        
        with pytest.raises(RuntimeError, match="not started"):
            await manager.execute_command("echo hello")
    
    @pytest.mark.asyncio
    async def test_execute_command_returns_result(self, temp_dir):
        """Test execute_command returns TerminalResult."""
        manager = TerminalSessionManager(session_factory=MockPtySession)
        
        await manager.ensure_started(temp_dir)
        result = await manager.execute_command("echo hello")
        
        assert isinstance(result, TerminalResult)
        assert "hello" in result.stdout
        assert not result.timed_out
        
        await manager.close()
    
    @pytest.mark.asyncio
    async def test_close_cleans_up(self, temp_dir):
        """Test close properly cleans up session."""
        manager = TerminalSessionManager(session_factory=MockPtySession)
        
        await manager.ensure_started(temp_dir)
        assert manager.is_started
        
        await manager.close()
        assert not manager.is_started
        assert manager.current_session is None


@pytest.mark.integration
class TestTerminalSessionManagerIntegration:
    """Integration tests using real PTY."""
    
    @pytest.mark.asyncio
    async def test_execute_echo_command(self, temp_dir):
        """Test executing a simple echo command."""
        manager = TerminalSessionManager()
        
        try:
            await manager.ensure_started(temp_dir)
            result = await manager.execute_command("echo 'test output'")
            
            assert "test output" in result.stdout
            assert not result.timed_out
        finally:
            await manager.close()
    
    @pytest.mark.asyncio
    async def test_cd_persistence(self, temp_dir):
        """Test that cd persists between commands."""
        import os
        manager = TerminalSessionManager()
        subdir = os.path.join(temp_dir, "subdir")
        os.makedirs(subdir)
        
        try:
            await manager.ensure_started(temp_dir)
            
            await manager.execute_command("cd subdir")
            result = await manager.execute_command("pwd")
            
            assert "subdir" in result.stdout
        finally:
            await manager.close()
    
    @pytest.mark.asyncio
    async def test_timeout_handling(self, temp_dir):
        """Test command timeout handling."""
        manager = TerminalSessionManager()
        
        try:
            await manager.ensure_started(temp_dir)
            result = await manager.execute_command("sleep 10", timeout_seconds=1)
            
            assert result.timed_out
        finally:
            await manager.close()
