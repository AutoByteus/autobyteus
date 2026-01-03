"""
Unit tests for background_process_manager.py
"""

import asyncio
import os
import pytest
import tempfile

from autobyteus.tools.terminal.background_process_manager import BackgroundProcessManager
from autobyteus.tools.terminal.types import BackgroundProcessOutput, ProcessInfo


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
    
    async def write(self, data: bytes):
        self._written.append(data)
        # Simulate output
        cmd = data.decode().strip()
        self._output_queue.append(f"Started: {cmd}\n".encode())
    
    async def read(self, timeout: float = 0.1):
        if self._output_queue:
            return self._output_queue.pop(0)
        return None
    
    async def close(self):
        self._alive = False


class TestBackgroundProcessManager:
    """Unit tests for BackgroundProcessManager."""
    
    @pytest.mark.asyncio
    async def test_start_process_returns_id(self, temp_dir):
        """Test start_process returns a process ID."""
        manager = BackgroundProcessManager(session_factory=MockPtySession)
        
        process_id = await manager.start_process("echo hello", temp_dir)
        
        assert process_id is not None
        assert process_id.startswith("bg_")
        
        await manager.stop_all()
    
    @pytest.mark.asyncio
    async def test_process_ids_unique(self, temp_dir):
        """Test each process gets unique ID."""
        manager = BackgroundProcessManager(session_factory=MockPtySession)
        
        id1 = await manager.start_process("cmd1", temp_dir)
        id2 = await manager.start_process("cmd2", temp_dir)
        id3 = await manager.start_process("cmd3", temp_dir)
        
        assert id1 != id2 != id3
        
        await manager.stop_all()
    
    @pytest.mark.asyncio
    async def test_get_output(self, temp_dir):
        """Test get_output returns BackgroundProcessOutput."""
        manager = BackgroundProcessManager(session_factory=MockPtySession)
        
        process_id = await manager.start_process("echo hello", temp_dir)
        
        # Give reader time to capture output
        await asyncio.sleep(0.2)
        
        result = manager.get_output(process_id)
        
        assert isinstance(result, BackgroundProcessOutput)
        assert result.process_id == process_id
        assert result.is_running
        
        await manager.stop_all()
    
    @pytest.mark.asyncio
    async def test_get_output_unknown_process_raises(self, temp_dir):
        """Test get_output raises KeyError for unknown process."""
        manager = BackgroundProcessManager(session_factory=MockPtySession)
        
        with pytest.raises(KeyError):
            manager.get_output("nonexistent")
    
    @pytest.mark.asyncio
    async def test_stop_process(self, temp_dir):
        """Test stop_process stops and removes process."""
        manager = BackgroundProcessManager(session_factory=MockPtySession)
        
        process_id = await manager.start_process("cmd", temp_dir)
        assert manager.process_count == 1
        
        success = await manager.stop_process(process_id)
        assert success
        assert manager.process_count == 0
    
    @pytest.mark.asyncio
    async def test_stop_unknown_process_returns_false(self, temp_dir):
        """Test stop_process returns False for unknown process."""
        manager = BackgroundProcessManager(session_factory=MockPtySession)
        
        success = await manager.stop_process("nonexistent")
        assert not success
    
    @pytest.mark.asyncio
    async def test_stop_all(self, temp_dir):
        """Test stop_all stops all processes."""
        manager = BackgroundProcessManager(session_factory=MockPtySession)
        
        await manager.start_process("cmd1", temp_dir)
        await manager.start_process("cmd2", temp_dir)
        await manager.start_process("cmd3", temp_dir)
        assert manager.process_count == 3
        
        count = await manager.stop_all()
        assert count == 3
        assert manager.process_count == 0
    
    @pytest.mark.asyncio
    async def test_list_processes(self, temp_dir):
        """Test list_processes returns all process info."""
        manager = BackgroundProcessManager(session_factory=MockPtySession)
        
        id1 = await manager.start_process("cmd1", temp_dir)
        id2 = await manager.start_process("cmd2", temp_dir)
        
        processes = manager.list_processes()
        
        assert len(processes) == 2
        assert id1 in processes
        assert id2 in processes
        assert isinstance(processes[id1], ProcessInfo)
        
        await manager.stop_all()


@pytest.mark.integration
class TestBackgroundProcessManagerIntegration:
    """Integration tests using real PTY."""
    
    @pytest.mark.asyncio
    async def test_start_and_get_output(self, temp_dir):
        """Test starting a real process and getting output."""
        manager = BackgroundProcessManager()
        
        try:
            process_id = await manager.start_process(
                "for i in 1 2 3; do echo line$i; sleep 0.1; done",
                temp_dir
            )
            
            # Wait for output
            await asyncio.sleep(0.5)
            
            result = manager.get_output(process_id)
            assert "line" in result.output
        finally:
            await manager.stop_all()
    
    @pytest.mark.asyncio
    async def test_stop_running_process(self, temp_dir):
        """Test stopping a long-running process."""
        manager = BackgroundProcessManager()
        
        try:
            process_id = await manager.start_process("sleep 100", temp_dir)
            
            await asyncio.sleep(0.2)
            assert manager.process_count == 1
            
            success = await manager.stop_process(process_id)
            assert success
            assert manager.process_count == 0
        finally:
            await manager.stop_all()
