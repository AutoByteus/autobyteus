"""
Integration tests for the BashExecutor module.
"""

import pytest
import tempfile
import os
from autobyteus.tools.bash.bash_executor import BashExecutor
from autobyteus.events.event_types import EventType
import subprocess


@pytest.fixture
def bash_executor():
    return BashExecutor()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_execute_valid_command(bash_executor):
    """
    Test executing a valid bash command.
    """
    command = "echo 'Integration Test'"
    expected_output = "Integration Test"

    result = await bash_executor.execute(command=command)
    assert result == expected_output


@pytest.mark.integration
@pytest.mark.asyncio
async def test_execute_invalid_command(bash_executor):
    """
    Test executing an invalid bash command to ensure proper error handling.
    """
    command = "invalid_command_xyz"

    with pytest.raises(subprocess.CalledProcessError) as exc_info:
        await bash_executor.execute(command=command)
    assert exc_info.value.returncode != 0
    # Removed locale-dependent assertion on stderr message


@pytest.mark.integration
@pytest.mark.asyncio
async def test_execute_command_creates_file(bash_executor):
    """
    Test executing a command that creates a file.
    """
    with tempfile.TemporaryDirectory() as temp_dir:
        filename = "test_file.txt"
        command = f"touch {os.path.join(temp_dir, filename)}"

        result = await bash_executor.execute(command=command)
        assert result == ""

        assert os.path.isfile(os.path.join(temp_dir, filename))


@pytest.mark.integration
@pytest.mark.asyncio
async def test_execute_command_with_spaces_in_path(bash_executor):
    """
    Test executing a command in a directory path that contains spaces.
    """
    with tempfile.TemporaryDirectory(prefix="test workspace ") as temp_dir:
        filename = "space_test.txt"
        escaped_path = temp_dir.replace(" ", "\\ ")
        command = f"touch {os.path.join(escaped_path, filename)}"

        result = await bash_executor.execute(command=command)
        assert result == ""

        assert os.path.isfile(os.path.join(temp_dir, filename))


@pytest.mark.integration
@pytest.mark.asyncio
async def test_execute_command_with_environment_variable(bash_executor):
    """
    Test executing a command that uses an environment variable.
    """
    command = "export TEST_VAR='HelloEnv' && echo $TEST_VAR"
    expected_output = "HelloEnv"

    result = await bash_executor.execute(command=command)
    assert result == expected_output


@pytest.mark.integration
@pytest.mark.asyncio
async def test_execute_command_with_error_output(bash_executor):
    """
    Test executing a command that produces error output.
    """
    command = "ls nonexistent_directory"

    with pytest.raises(subprocess.CalledProcessError) as exc_info:
        await bash_executor.execute(command=command)
    assert exc_info.value.returncode != 0
    # Removed locale-dependent assertion on stderr message