"""
Unit tests for terminal tool functions.
"""

import asyncio
import pytest
import tempfile

# Import the underlying functions, not the FunctionalTool wrappers
from autobyteus.tools.terminal.tools.run_bash import run_bash as run_cmd_tool
from autobyteus.tools.terminal.tools.start_background_process import start_background_process as start_bg_tool
from autobyteus.tools.terminal.tools.get_process_output import get_process_output as get_output_tool
from autobyteus.tools.terminal.tools.stop_background_process import stop_background_process as stop_bg_tool
from autobyteus.tools.terminal.types import TerminalResult


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


@pytest.mark.integration
class TestRunBashTool:
    """Integration tests for run_bash tool."""
    
    @pytest.mark.asyncio
    async def test_simple_echo(self, temp_dir):
        """Test simple echo command."""
        context = MockContext(temp_dir)
        # Use .execute() method on FunctionalTool
        result = await run_cmd_tool.execute(context, command="echo hello")
        
        assert isinstance(result, TerminalResult)
        assert "hello" in result.stdout
        assert not result.timed_out
    
    @pytest.mark.asyncio
    async def test_cd_persists(self, temp_dir):
        """Test cd persists between calls."""
        import os
        context = MockContext(temp_dir)
        
        # Create subdirectory
        subdir = os.path.join(temp_dir, "mysubdir")
        os.makedirs(subdir)
        
        # cd into it
        await run_cmd_tool.execute(context, command="cd mysubdir")
        
        # Verify we're in the subdir
        result = await run_cmd_tool.execute(context, command="pwd")
        assert "mysubdir" in result.stdout
    
    @pytest.mark.asyncio
    async def test_timeout(self, temp_dir):
        """Test command timeout."""
        context = MockContext(temp_dir)
        result = await run_cmd_tool.execute(
            context, 
            command="sleep 5", 
            timeout_seconds=1
        )
        
        assert result.timed_out


@pytest.mark.integration
class TestBackgroundProcessTools:
    """Integration tests for background process tools."""
    
    @pytest.mark.asyncio
    async def test_start_get_stop_lifecycle(self, temp_dir):
        """Test full lifecycle: start -> get output -> stop."""
        context = MockContext(temp_dir)
        
        # Start a process
        start_result = await start_bg_tool.execute(
            context,
            command="for i in 1 2 3; do echo line$i; sleep 0.1; done; sleep 10"
        )
        
        assert "process_id" in start_result
        assert start_result["status"] == "started"
        process_id = start_result["process_id"]
        
        # Wait for some output
        await asyncio.sleep(0.5)
        
        # Get output
        output_result = await get_output_tool.execute(context, process_id=process_id)
        
        assert "output" in output_result
        assert output_result["is_running"]
        
        # Stop the process
        stop_result = await stop_bg_tool.execute(context, process_id=process_id)
        
        assert stop_result["status"] == "stopped"
    
    @pytest.mark.asyncio
    async def test_stop_nonexistent_process(self, temp_dir):
        """Test stopping a nonexistent process."""
        context = MockContext(temp_dir)
        
        result = await stop_bg_tool.execute(
            context, 
            process_id="nonexistent_123"
        )
        
        assert result["status"] == "not_found"
    
    @pytest.mark.asyncio
    async def test_get_output_nonexistent_process(self, temp_dir):
        """Test getting output from nonexistent process."""
        context = MockContext(temp_dir)
        
        result = await get_output_tool.execute(
            context,
            process_id="nonexistent_123"
        )
        
        assert "error" in result
        assert not result["is_running"]

