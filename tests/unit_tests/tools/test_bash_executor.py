import pytest
from src.tools.bash_executor import BashExecutor

# Tests for BashExecutor
@pytest.mark.parametrize('command, expected_output', [
    ('echo BDD Test', 'BDD Test'),
])
def test_bash_executor(command, expected_output):
    bash_exec = BashExecutor()
    result = bash_exec.execute(command)
    assert result == expected_output

