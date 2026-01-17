"""
Windows-specific integration tests for WSL terminal functionality.

This file contains tests that should ONLY run on Windows with WSL installed.
These tests are separate from the Unix PTY tests to avoid importing fcntl
and other Unix-only modules.

Run these tests on Windows with:
    uv run python -m pytest tests/unit_tests/tools/terminal/test_wsl_terminal_windows.py -v

Or run with the windows marker:
    uv run python -m pytest -v -m "windows"
"""

import asyncio
import os
import pytest
import tempfile
import subprocess

# Only import WSL-specific modules (no Unix dependencies)
from autobyteus.tools.terminal.wsl_tmux_session import WslTmuxSession
from autobyteus.tools.terminal import wsl_utils
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

@pytest.fixture(autouse=True)
def require_tmux():
    """Skip tests if tmux is not available in the WSL distro."""
    try:
        wsl_exe = wsl_utils.ensure_wsl_available()
        wsl_utils.ensure_wsl_distro_available(wsl_exe)
        distro = wsl_utils.select_wsl_distro(wsl_exe)
        result = subprocess.run(
            [wsl_exe, "-d", distro, "--exec", "tmux", "-V"],
            capture_output=True,
            text=False,
            check=False,
            timeout=5,
        )
        if result.returncode != 0:
            pytest.skip("tmux is required in WSL for Windows terminal tests.")
    except Exception as exc:
        pytest.skip(f"tmux is required in WSL for Windows terminal tests: {exc}")


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
class TestWslTmuxSession:
    """Integration tests for WslTmuxSession on Windows."""
    
    @pytest.mark.asyncio
    async def test_wsl_session_start_and_alive(self, temp_dir):
        """Test that WSL session can start and reports as alive."""
        session = WslTmuxSession("wsl-test-001")
        
        try:
            await session.start(temp_dir)
            assert session.is_alive
        finally:
            await session.close()
        
        assert not session.is_alive
    
    @pytest.mark.asyncio
    async def test_wsl_echo_command(self, temp_dir):
        """Test executing a simple echo command in WSL."""
        session = WslTmuxSession("wsl-test-002")
        
        try:
            await session.start(temp_dir)
            
            # Write echo command
            await session.write(b"echo 'Hello from WSL'\\n")
            
            # Read output - give more time for WSL to respond
            output = b""
            for _ in range(30):  # Try up to 3 seconds
                data = await session.read(timeout=0.1)
                if data:
                    output += data
                # Check decoded string for the text (handles escape codes better)
                if "Hello from WSL" in output.decode('utf-8', errors='ignore'):
                    break
            
            # Decode and check - ANSI escape codes are OK, we just need the text
            output_str = output.decode('utf-8', errors='ignore')
            assert "Hello from WSL" in output_str, f"Expected 'Hello from WSL' in output, got: {repr(output_str)}"
        finally:
            await session.close()
    
    @pytest.mark.asyncio
    async def test_wsl_pwd_command(self, temp_dir):
        """Test that pwd command works and shows WSL path format."""
        manager = TerminalSessionManager()
        
        try:
            await manager.ensure_started(temp_dir)
            result = await manager.execute_command("pwd")
            assert "/mnt/" in result.stdout or "/" in result.stdout
        finally:
            await manager.close()


@pytest.mark.windows
@pytest.mark.integration
class TestWslTerminalSessionManager:
    """Integration tests for TerminalSessionManager using WSL."""
    
    @pytest.mark.asyncio
    async def test_manager_with_wsl_backend(self, temp_dir):
        """Test that TerminalSessionManager uses WSL on Windows."""
        # On Windows, this should automatically use WslTmuxSession
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

    @pytest.mark.asyncio
    async def test_run_bash_creates_file_in_windows_workspace(self, temp_dir):
        """Test that WSL writes into the Windows workspace path."""
        context = MockContext(temp_dir)
        filename = "wsl_created_file.txt"
        file_path = os.path.join(temp_dir, filename)

        result = await run_cmd_tool.execute(
            context,
            command=f"echo 'hello' > {filename}",
        )

        assert isinstance(result, TerminalResult)
        assert not result.timed_out
        assert os.path.isfile(file_path)

    @pytest.mark.asyncio
    async def test_run_bash_chained_commands(self, temp_dir):
        """Test chained commands with working directory changes."""
        context = MockContext(temp_dir)

        result = await run_cmd_tool.execute(
            context,
            command="mkdir -p chain_test/inner && cd chain_test && echo 'ok' > inner/file.txt && cat inner/file.txt",
        )

        assert isinstance(result, TerminalResult)
        assert "ok" in result.stdout
        assert not result.timed_out

    @pytest.mark.asyncio
    async def test_run_bash_pipes_and_redirects(self, temp_dir):
        """Test pipes and redirects produce expected output."""
        context = MockContext(temp_dir)

        result = await run_cmd_tool.execute(
            context,
            command="printf 'a\\nb\\n' | wc -l",
        )

        assert isinstance(result, TerminalResult)
        output_digits = "".join(ch for ch in result.stdout if ch.isdigit())
        assert output_digits == "2"

    @pytest.mark.asyncio
    async def test_run_bash_env_var_persistence(self, temp_dir):
        """Test environment variable set and read in the same command."""
        context = MockContext(temp_dir)

        result = await run_cmd_tool.execute(
            context,
            command="export AUTOBYTEUS_TEST_VAR=hello && echo $AUTOBYTEUS_TEST_VAR",
        )

        assert isinstance(result, TerminalResult)
        assert "hello" in result.stdout

    @pytest.mark.asyncio
    async def test_run_bash_exit_code(self, temp_dir):
        """Test that non-zero exit codes are captured."""
        context = MockContext(temp_dir)

        result = await run_cmd_tool.execute(
            context,
            command="false",
        )

        assert isinstance(result, TerminalResult)
        assert result.exit_code == 1
