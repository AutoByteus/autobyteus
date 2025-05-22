import pytest
import asyncio
import subprocess
from unittest.mock import AsyncMock, patch, Mock # Added Mock
from autobyteus.tools.bash.bash_executor import BashExecutor
from autobyteus.events.event_types import EventType

# Added mock_agent_context fixture
@pytest.fixture
def mock_agent_context():
    mock_context = Mock()
    mock_context.agent_id = "test_agent_123"
    return mock_context

@pytest.fixture
def bash_executor():
    return BashExecutor()


@pytest.mark.asyncio
async def test_should_execute_bash_command_and_return_output(bash_executor, mock_agent_context): # Added mock_agent_context
    command = "echo 'BDD Test'"
    expected_output = "BDD Test"

    # Mock subprocess for predictable output
    with patch('asyncio.create_subprocess_shell') as mock_subprocess:
        mock_process = AsyncMock()
        mock_process.communicate.return_value = (b"BDD Test\n", b"")
        mock_process.returncode = 0
        mock_subprocess.return_value = mock_process

        result = await bash_executor.execute(mock_agent_context, command=command) # Added mock_agent_context
        assert result == expected_output


@pytest.mark.asyncio
async def test_execute_without_command_raises_value_error(bash_executor, mock_agent_context): # Added mock_agent_context
    with pytest.raises(ValueError) as exc_info:
        await bash_executor.execute(mock_agent_context) # Added mock_agent_context
    assert "The 'command' keyword argument must be specified." in str(exc_info.value)


@pytest.mark.asyncio
async def test_execute_command_failure(bash_executor, mock_agent_context): # Added mock_agent_context
    command = "invalid_command_xyz"
    error_message = "bash: invalid_command_xyz: command not found"

    with patch('asyncio.create_subprocess_shell') as mock_subprocess:
        mock_process = AsyncMock()
        mock_process.communicate.return_value = (b"", error_message.encode())
        mock_process.returncode = 127
        mock_subprocess.return_value = mock_process

        with pytest.raises(subprocess.CalledProcessError) as exc_info:
            await bash_executor.execute(mock_agent_context, command=command) # Added mock_agent_context
        
        assert exc_info.value.returncode == 127
        # The actual error message in CalledProcessError.stderr might not have "bash: " prefix
        # depending on how it's captured. Let's check if the core message is present.
        assert "invalid_command_xyz: command not found" in exc_info.value.stderr


@pytest.mark.asyncio
async def test_tool_usage_xml(bash_executor):
    expected_usage = '''BashExecutor: Executes bash commands and retrieves their output. Usage:
    <command name="BashExecutor">
        <arg name="command">bash command</arg>
    </command>
    where "bash command" is a string containing the command to be executed.
    '''
    assert bash_executor.tool_usage_xml() == expected_usage


def test_get_name():
    assert BashExecutor.get_name() == "BashExecutor"


@pytest.mark.asyncio
async def test_execute_with_complex_command(bash_executor, mock_agent_context): # Added mock_agent_context
    command = "ls -la | grep test"
    expected_output = "test file output"

    with patch('asyncio.create_subprocess_shell') as mock_subprocess:
        mock_process = AsyncMock()
        mock_process.communicate.return_value = (expected_output.encode(), b"")
        mock_process.returncode = 0
        mock_subprocess.return_value = mock_process

        result = await bash_executor.execute(mock_agent_context, command=command) # Added mock_agent_context
        assert result == expected_output


@pytest.mark.asyncio
async def test_execute_empty_output(bash_executor, mock_agent_context): # Added mock_agent_context
    command = "true"  # Command that produces no output

    with patch('asyncio.create_subprocess_shell') as mock_subprocess:
        mock_process = AsyncMock()
        mock_process.communicate.return_value = (b"", b"")
        mock_process.returncode = 0
        mock_subprocess.return_value = mock_process

        result = await bash_executor.execute(mock_agent_context, command=command) # Added mock_agent_context
        assert result == ""


@pytest.mark.asyncio
async def test_execute_with_stderr_on_success(bash_executor, mock_agent_context): # Added mock_agent_context
    command = "echo 'warning' >&2 && echo 'success'"
    
    with patch('asyncio.create_subprocess_shell') as mock_subprocess:
        mock_process = AsyncMock()
        mock_process.communicate.return_value = (b"success\n", b"warning\n")
        mock_process.returncode = 0
        mock_subprocess.return_value = mock_process

        result = await bash_executor.execute(mock_agent_context, command=command) # Added mock_agent_context
        assert result == "success"
