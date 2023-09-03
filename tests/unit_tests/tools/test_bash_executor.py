import pytest
from autobyteus.tools.bash_executor import BashExecutor

@pytest.fixture
def bash_executor():
    return BashExecutor()


def test_should_execute_bash_command_and_return_output(bash_executor):
    command = "echo BDD Test"
    expected_output = "BDD Test"
    result = bash_executor.execute(command)
    assert result == expected_output


