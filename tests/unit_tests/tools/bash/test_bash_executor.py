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
from autobyteus.tools.bash.types import BashExecutionResult
from autobyteus.tools.registry import default_tool_registry
from autobyteus.agent.context import AgentContext

TOOL_NAME = "execute_bash"

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

# -- Schema and Definition Unit Tests --

def test_bash_executor_definition_is_registered():
    """Tests that the tool is correctly registered in the default registry."""
    definition = default_tool_registry.get_tool_definition(TOOL_NAME)
    assert definition is not None
    assert definition.name == TOOL_NAME
    # Test the updated description explaining the structured return type
    assert "returns a structured result" in definition.description
    assert "does NOT raise an exception" in definition.description
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
    """Unit test: checks for FileNotFoundError if 'bash' is not in PATH (pre-execution failure)."""
    with pytest.raises(FileNotFoundError, match="'bash' executable not found"):
        await bash_executor.execute(context=mock_context_no_workspace, command="echo 'test'")

@pytest.mark.asyncio
@patch('tempfile.gettempdir', return_value='/tmp/mock_temp_dir')
@patch('asyncio.create_subprocess_exec')
@patch('shutil.which', return_value='/bin/bash')
async def test_unit_uses_temp_dir_as_fallback(mock_shutil, mock_subprocess, mock_gettempdir, mock_context_no_workspace):
    """Unit test: verifies that the system's temp directory is used as CWD when no workspace exists."""
    mock_process = AsyncMock(returncode=0)
    mock_process.communicate.return_value = (b"success output", b"warning log")
    mock_subprocess.return_value = mock_process

    result = await bash_executor.execute(context=mock_context_no_workspace, command="ls")
    
    assert isinstance(result, BashExecutionResult)
    assert result.exit_code == 0
    assert result.stdout == "success output"
    assert result.stderr == "warning log"

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
    
    result = await bash_executor.execute(context=real_workspace_context, command="pwd")
    
    assert isinstance(result, BashExecutionResult)
    assert result.exit_code == 0
    assert result.stderr == ""
    assert os.path.samefile(result.stdout, workspace_path)

@pytest.mark.asyncio
@pytest.mark.skipif(not shutil.which("bash"), reason="bash executable not found in PATH")
@pytest.mark.skipif(not shutil.which("node"), reason="node.js executable not found in PATH")
async def test_integration_write_and_run_node_script(real_workspace_context):
    """
    Integration test: Uses execute_bash to first write a JS file and then
    execute it with Node, all within a real temporary workspace.
    """
    workspace_path = Path(real_workspace_context.workspace.get_base_path())
    js_file_path = workspace_path / "hello.js"
    
    js_content = "console.log('Hello from file');"
    write_command = f"echo \"{js_content}\" > hello.js"
    
    write_result = await bash_executor.execute(context=real_workspace_context, command=write_command)
    
    assert isinstance(write_result, BashExecutionResult)
    assert write_result.exit_code == 0
    assert write_result.stdout == ""
    assert js_file_path.is_file()
    assert js_file_path.read_text().strip() == js_content
    
    run_command = "node hello.js"
    run_result = await bash_executor.execute(context=real_workspace_context, command=run_command)
    
    assert isinstance(run_result, BashExecutionResult)
    assert run_result.exit_code == 0
    assert run_result.stdout == "Hello from file"

@pytest.mark.asyncio
@pytest.mark.skipif(not shutil.which("ffmpeg"), reason="ffmpeg executable not found in PATH")
async def test_integration_ffmpeg_returns_logs_on_success(real_workspace_context):
    """
    Integration test: Verifies that a tool like ffmpeg, which logs progress to stderr
    on success, has its diagnostic output captured.
    """
    workspace_path = Path(real_workspace_context.workspace.get_base_path())
    generate_cmd = "ffmpeg -f lavfi -i testsrc=size=160x120:rate=10:duration=1 -y -loglevel error input.mp4"
    await bash_executor.execute(context=real_workspace_context, command=generate_cmd)

    cut_cmd = "ffmpeg -i input.mp4 -t 0.5 -y output.mp4"
    cut_result = await bash_executor.execute(context=real_workspace_context, command=cut_cmd)
    
    assert isinstance(cut_result, BashExecutionResult)
    assert cut_result.exit_code == 0
    assert cut_result.stdout == "" # ffmpeg does not print to stdout in this case
    assert "ffmpeg version" in cut_result.stderr
    assert "frame=" in cut_result.stderr

@pytest.mark.asyncio
@pytest.mark.skipif(not shutil.which("bash"), reason="bash executable not found in PATH")
async def test_integration_failed_command_returns_result_object_with_error_details(real_workspace_context):
    """
    Integration test: Verifies that a failed command does NOT raise an exception,
    but instead returns a BashExecutionResult with a non-zero exit code and a
    predictable, locale-independent stderr content.
    """
    # This command is guaranteed to fail with a specific exit code and stderr message,
    # regardless of system language settings.
    invalid_cmd = "echo 'This is a controlled error message.' >&2; exit 42"
    
    result = await bash_executor.execute(context=real_workspace_context, command=invalid_cmd)
        
    assert isinstance(result, BashExecutionResult)
    assert result.exit_code == 42
    assert result.stdout == ""
    assert "This is a controlled error message." in result.stderr

@pytest.mark.asyncio
@pytest.mark.skipif(not shutil.which("rg"), reason="ripgrep (rg) not found in PATH")
async def test_integration_rg_with_permission_error_returns_partial_success(real_workspace_context):
    """
    Integration test for the original bug: `rg` with permission errors should return
    a result object containing both the successful matches (stdout) and the errors (stderr).
    """
    workspace_path = Path(real_workspace_context.workspace.get_base_path())
    
    # 1. Create a readable file with a match
    readable_file = workspace_path / "search.txt"
    readable_file.write_text("Here is the AUTOBYTEUS_VNC_SERVER_URL variable.")
    
    # 2. Create a directory and an unreadable file inside it
    secrets_dir = workspace_path / "secrets"
    secrets_dir.mkdir()
    unreadable_file = secrets_dir / "key.pem"
    unreadable_file.write_text("some secret")
    # Make the file unreadable by the owner/group/others
    os.chmod(unreadable_file, 0o000)

    # 3. Run the rg command
    # The command should find the text in the readable file but fail on the unreadable one
    command = 'rg "AUTOBYTEUS_VNC_SERVER_URL" .'
    result = await bash_executor.execute(context=real_workspace_context, command=command)
    
    # 4. Assert the partial success conditions
    assert isinstance(result, BashExecutionResult)
    # rg exits with 2 on error, but this can be platform-dependent. Just check for non-zero.
    assert result.exit_code != 0
    # stdout should contain the match it found
    assert "AUTOBYTEUS_VNC_SERVER_URL" in result.stdout
    assert "search.txt" in result.stdout
    # stderr should contain the permission denied error
    assert "Permission denied" in result.stderr
    assert "key.pem" in result.stderr
