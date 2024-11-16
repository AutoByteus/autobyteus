import pytest
import asyncio
import subprocess
from autobyteus.tools.bash.bash_executor import BashExecutor
from autobyteus.events.event_types import EventType


@pytest.fixture
def bash_executor():
    return BashExecutor()


@pytest.mark.asyncio
async def test_should_execute_bash_command_and_return_output(bash_executor, mocker):
    command = "echo 'BDD Test'"
    expected_output = "BDD Test"

    # Mock the _execute method to return expected output
    mocker.patch.object(bash_executor, '_execute', return_value=expected_output)

    result = await bash_executor.execute(command=command)
    assert result == expected_output


@pytest.mark.asyncio
async def test_execute_without_command_raises_value_error(bash_executor):
    with pytest.raises(ValueError) as exc_info:
        await bash_executor.execute()
    assert "The 'command' keyword argument must be specified." in str(exc_info.value)


@pytest.mark.asyncio
async def test_execute_command_failure(bash_executor, mocker):
    command = "invalid_command_xyz"
    error_message = "bash: invalid_command_xyz: command not found"

    # Mock the _execute method to raise CalledProcessError
    mocker.patch.object(
        bash_executor,
        '_execute',
        side_effect=subprocess.CalledProcessError(
            returncode=127,
            cmd=command,
            output='',
            stderr=error_message
        )
    )

    with pytest.raises(subprocess.CalledProcessError) as exc_info:
        await bash_executor.execute(command=command)
    assert exc_info.value.returncode == 127
    assert exc_info.value.stderr == error_message