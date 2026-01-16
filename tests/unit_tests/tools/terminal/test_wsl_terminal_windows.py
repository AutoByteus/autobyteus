"""
Windows-specific integration tests for WSL terminal functionality.

This file contains tests that should ONLY run on Windows with WSL installed.
These tests are separate from the Unix PTY tests to avoid importing fcntl
and other Unix-only modules.

Run these tests on Windows with:
    python -m pytest tests/unit_tests/tools/terminal/test_wsl_terminal_windows.py -v

Or run with the windows marker:
    python -m pytest -v -m "windows"
"""

import asyncio
import os
import pytest
import tempfile

# Only import WSL-specific modules (no Unix dependencies)
from autobyteus.tools.terminal.wsl_pty_session import WslPtySession
from autobyteus.tools.terminal.terminal_session_manager import TerminalSessionManager
from autobyteus.tools.terminal.types import TerminalResult

# Import tool functions
from autobyteus.tools.terminal.tools.run_bash import run_bash as run_cmd_tool
from autobyteus.tools.terminal.tools.start_background_process import start_background_process as start_bg_tool
from autobyteus.tools.terminal.tools.get_process_output import get_process_output as get_output_tool
from autobyteus.tools.terminal.tools.stop_background_process import stop_background_process as stop_bg_tool


# Skip all tests in this file if not on Windows
pytestmark = pytest.mark.skipif(
    os.name != "nt",
    reason="Windows-specific tests - requires Windows OS and WSL"
)


@pytest.fixture
def temp_dir():
    """Create a temporary directory for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


class MockContext:
    """Mock agent context for testing."""
    
    def __init__(self, base_path: str):
        self.workspace = MockWorkspace(base_path)
        self.agent_id = "test-agent-001"


class MockWorkspace:
    """Mock workspace."""
    
    def __init__(self, base_path: str):
        self._base_path = base_path
    
    def get_base_path(self) -> str:
        return self._base_path


@pytest.mark.windows
@pytest.mark.integration
class TestWslPtySession:
    """Integration tests for WslPtySession on Windows."""
    
    @pytest.mark.asyncio
    async def test_wsl_session_start_and_alive(self, temp_dir):
        """Test that WSL session can start and reports as alive."""
        session = WslPtySession("wsl-test-001")
        
        try:
            await session.start(temp_dir)
            assert session.is_alive
        finally:
            await session.close()
        
        assert not session.is_alive
    
    @pytest.mark.asyncio
    async def test_wsl_echo_command(self, temp_dir):
        """Test executing a simple echo command in WSL."""
        session = WslPtySession("wsl-test-002")
        
        try:
            await session.start(temp_dir)
            
            # Write echo command
            await session.write(b"echo 'Hello from WSL'\\n")
            
            # Read output
            output = b""
            for _ in range(20):  # Try up to 2 seconds
                data = await session.read(timeout=0.1)
                if data:
                    output += data
                if b"Hello from WSL" in output:
                    break
            
            assert b"Hello from WSL" in output
        finally:
            await session.close()
    
    @pytest.mark.asyncio
    async def test_wsl_pwd_command(self, temp_dir):
        """Test that pwd command works and shows WSL path format."""
        session = WslPtySession("wsl-test-003")
        
        try:
            await session.start(temp_dir)
            
            # Run pwd command
            await session.write(b"pwd\\n")
            
            # Read output
            output = b""
            for _ in range(20):
                data = await session.read(timeout=0.1)
                if data:
                    output += data
                # WSL paths start with /mnt/ for Windows drives
                if b"/mnt/" in output or b"pwd" in output:
                    break
            
            # Should contain WSL path format
            output_str = output.decode('utf-8', errors='ignore')
            assert "/mnt/" in output_str or "/" in output_str
        finally:
            await session.close()


@pytest.mark.windows
@pytest.mark.integration
class TestWslTerminalSessionManager:
    """Integration tests for TerminalSessionManager using WSL."""
    
    @pytest.mark.asyncio
    async def test_manager_with_wsl_backend(self, temp_dir):
        """Test that TerminalSessionManager uses WSL on Windows."""
        # On Windows, this should automatically use WslPtySession
        manager = TerminalSessionManager()
        
        try:
            await manager.ensure_started(temp_dir)
            assert manager.is_started
            
            # Execute a simple command
            result = await manager.execute_command("echo 'WSL test'")
            
            assert isinstance(result, TerminalResult)
            assert "WSL test" in result.stdout
            assert not result.timed_out
        finally:
            await manager.close()
    
    @pytest.mark.asyncio
    async def test_cd_persistence_in_wsl(self, temp_dir):
        """Test that cd persists between commands in WSL."""
        manager = TerminalSessionManager()
        
        try:
            await manager.ensure_started(temp_dir)
            
            # Create a subdirectory first
            await manager.execute_command("mkdir -p testsubdir")
            
            # cd into it
            await manager.execute_command("cd testsubdir")
            
            # Verify we're in the subdirectory
            result = await manager.execute_command("pwd")
            assert "testsubdir" in result.stdout
        finally:
            await manager.close()


@pytest.mark.windows
@pytest.mark.integration
class TestWslTerminalTools:
    """Integration tests for terminal tools using WSL."""
    
    @pytest.mark.asyncio
    async def test_run_bash_simple_command(self, temp_dir):
        """Test run_bash tool with a simple echo command."""
        context = MockContext(temp_dir)
        
        result = await run_cmd_tool.execute(context, command="echo 'Testing WSL'")
        
        assert isinstance(result, TerminalResult)
        assert "Testing WSL" in result.stdout
        assert not result.timed_out
    
    @pytest.mark.asyncio
    async def test_run_bash_timeout(self, temp_dir):
        """Test that timeout works correctly in WSL."""
        context = MockContext(temp_dir)
        
        result = await run_cmd_tool.execute(
            context,
            command="sleep 5",
            timeout_seconds=1
        )
        
        assert result.timed_out
    
    @pytest.mark.asyncio
    async def test_background_process_lifecycle(self, temp_dir):
        """Test full background process lifecycle in WSL."""
        context = MockContext(temp_dir)
        
        # Start a background process
        start_result = await start_bg_tool.execute(
            context,
            command="for i in 1 2 3; do echo line$i; sleep 0.2; done; sleep 10"
        )
        
        assert "process_id" in start_result
        assert start_result["status"] == "started"
        process_id = start_result["process_id"]
        
        # Wait for some output
        await asyncio.sleep(0.8)
        
        # Get output
        output_result = await get_output_tool.execute(context, process_id=process_id)
        
        assert "output" in output_result
        assert output_result["is_running"]
        # Should have at least some lines
        assert "line" in output_result["output"]
        
        # Stop the process
        stop_result = await stop_bg_tool.execute(context, process_id=process_id)
        
        assert stop_result["status"] == "stopped"
    
    @pytest.mark.asyncio
    async def test_which_bash_in_wsl(self, temp_dir):
        """Test that we can locate bash inside WSL."""
        context = MockContext(temp_dir)
        
        result = await run_cmd_tool.execute(context, command="which bash")
        
        assert isinstance(result, TerminalResult)
        assert "/bin/bash" in result.stdout or "/usr/bin/bash" in result.stdout
