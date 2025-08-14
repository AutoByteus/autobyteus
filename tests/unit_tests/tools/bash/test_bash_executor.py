# file: tests/unit_tests/tools/bash/test_bash_executor.py
import pytest
import asyncio
import subprocess
from unittest.mock import AsyncMock, patch, Mock
import xml.sax.saxutils
import tempfile
from pathlib import Path
import os
import shutil

# Import the function directly for testing, the @tool decorator handles registration
from autobyteus.tools.bash.bash_executor import bash_executor
from autobyteus.tools.registry import default_tool_registry
from autobyteus.agent.context import AgentContext

TOOL_NAME = "BashExecutor"

# -- Fixtures --

@pytest.fixture
def real_workspace_context():
    """
    Pytest fixture that creates a real temporary directory to act as an agent's workspace.
    It yields an AgentContext pointing to this directory and cleans up automatically.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        workspace_path = Path(tmpdir)
        
        mock_workspace = Mock()
        mock_workspace.get_base_path.return_value = str(workspace_path)
        
        mock_context = Mock(spec=AgentContext)
        mock_context.agent_id = "test_agent_real_ws"
        mock_context.workspace = mock_workspace
        
        yield mock_context
    # The 'with' statement ensures the temporary directory is removed after the test

@pytest.fixture
def mock_context_no_workspace():
    """Provides an AgentContext without a workspace for fallback testing."""
    mock_context = Mock(spec=AgentContext)
    mock_context.agent_id = "test_agent_no_ws"
    mock_context.workspace = None
    return mock_context

# -- Schema and Definition Unit Tests (No Change) --

def test_bash_executor_definition_is_registered():
    """Tests that the tool is correctly registered in the default registry."""
    definition = default_tool_registry.get_tool_definition(TOOL_NAME)
    assert definition is not None
    assert definition.name == TOOL_NAME
    assert "Executes bash commands" in definition.description
    assert definition.argument_schema is not None
    
    arg_names = [p.name for p in definition.argument_schema.parameters]
    assert arg_names == ["command"]

def test_bash_executor_schema_only_has_command_arg():
    """Ensures the schema correctly reflects that 'command' is the only argument."""
    definition = default_tool_registry.get_tool_definition(TOOL_NAME)
    assert definition is not None
    
    # XML Schema Check
    xml_output = definition.get_usage_xml()
    assert '<arg name="command" type="string"' in xml_output
    assert '<arg name="cwd"' not in xml_output

    # JSON Schema Check
    json_output = definition.get_usage_json()
    properties = json_output["inputSchema"]["properties"]
    assert "command" in properties
    assert "cwd" not in properties
    assert "command" in json_output["inputSchema"]["required"]

# -- Unit Tests for Specific Logic/Failures --

@pytest.mark.asyncio
@patch('shutil.which', return_value=None)
async def test_unit_raises_error_if_bash_not_found(mock_shutil_which, mock_context_no_workspace):
    """Unit test: checks for FileNotFoundError if 'bash' is not in PATH."""
    with pytest.raises(FileNotFoundError, match="'bash' executable not found"):
        # FIX: Call the .execute() method on the tool instance
        await bash_executor.execute(context=mock_context_no_workspace, command="echo 'test'")

@pytest.mark.asyncio
@patch('tempfile.gettempdir', return_value='/tmp/mock_temp_dir')
@patch('asyncio.create_subprocess_exec')
@patch('shutil.which', return_value='/bin/bash')
async def test_unit_uses_temp_dir_as_fallback(mock_shutil, mock_subprocess, mock_gettempdir, mock_context_no_workspace):
    """Unit test: verifies that the system's temp directory is used as CWD when no workspace exists."""
    mock_process = AsyncMock(returncode=0)
    mock_process.communicate.return_value = (b"done", b"")
    mock_subprocess.return_value = mock_process

    # FIX: Call the .execute() method on the tool instance
    await bash_executor.execute(context=mock_context_no_workspace, command="ls")

    mock_subprocess.assert_called_once()
    call_kwargs = mock_subprocess.call_args[1]
    assert call_kwargs['cwd'] == "/tmp/mock_temp_dir"
    mock_gettempdir.assert_called_once()

# -- Integration-Style Tests (Using Real Subprocesses and Filesystem) --

@pytest.mark.asyncio
@pytest.mark.skipif(not shutil.which("bash"), reason="bash executable not found in PATH")
async def test_integration_pwd_command_returns_real_workspace_path(real_workspace_context):
    """Integration test: Verifies CWD is set correctly by running 'pwd'."""
    workspace_path = real_workspace_context.workspace.get_base_path()
    
    # FIX: Call the .execute() method on the tool instance
    result = await bash_executor.execute(context=real_workspace_context, command="pwd")
    
    # os.path.samefile correctly compares paths, handling symlinks etc.
    assert os.path.samefile(result, workspace_path)

@pytest.mark.asyncio
@pytest.mark.skipif(not shutil.which("bash"), reason="bash executable not found in PATH")
@pytest.mark.skipif(not shutil.which("node"), reason="node.js executable not found in PATH")
async def test_integration_write_and_run_node_script(real_workspace_context):
    """
    Integration test: Uses BashExecutor to first write a JS file and then
    execute it with Node, all within a real temporary workspace.
    """
    workspace_path = Path(real_workspace_context.workspace.get_base_path())
    js_file_path = workspace_path / "hello.js"
    
    # Step 1: Write the "hello.js" file into the workspace using the tool
    js_content = "console.log('Hello from file');"
    # Use a relative path in the command; the tool will run it inside the workspace
    write_command = f"echo \"{js_content}\" > hello.js"
    
    # FIX: Call the .execute() method on the tool instance
    write_result = await bash_executor.execute(context=real_workspace_context, command=write_command)
    
    # Assert that the write command succeeded (it produces no stdout) and the file exists
    assert write_result == ""
    assert js_file_path.is_file()
    assert js_file_path.read_text().strip() == js_content
    
    # Step 2: Run the "hello.js" file using the tool
    run_command = "node hello.js"
    
    # FIX: Call the .execute() method on the tool instance
    run_result = await bash_executor.execute(context=real_workspace_context, command=run_command)
    
    # Assert the output is correct
    assert run_result == "Hello from file"
