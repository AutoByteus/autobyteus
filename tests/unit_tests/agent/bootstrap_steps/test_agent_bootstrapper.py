# file: autobyteus/tests/unit_tests/agent/bootstrap_steps/test_agent_bootstrapper.py
import logging
from unittest.mock import AsyncMock, patch

import pytest

from autobyteus.agent.bootstrap_steps.agent_bootstrapper import AgentBootstrapper
from autobyteus.agent.bootstrap_steps.base_bootstrap_step import BaseBootstrapStep

# Define dummy classes for spec'ing mocks. This is more robust than
# manually assigning __class__.__name__.
class MockStep1(BaseBootstrapStep):
    async def execute(self, context):
        # This method will be mocked by AsyncMock anyway, so its content doesn't matter.
        pass

class MockStep2(BaseBootstrapStep):
    async def execute(self, context):
        # This method will be mocked by AsyncMock anyway, so its content doesn't matter.
        pass

@pytest.fixture
def mock_step_1():
    step = AsyncMock(spec=MockStep1)
    # The name is now derived from the spec class `MockStep1`
    step.execute.return_value = True
    return step

@pytest.fixture
def mock_step_2():
    step = AsyncMock(spec=MockStep2)
    # The name is now derived from the spec class `MockStep2`
    step.execute.return_value = True
    return step

def test_bootstrapper_initialization_default(caplog):
    """Test that the bootstrapper initializes with default steps if none are provided."""
    with patch('autobyteus.agent.bootstrap_steps.agent_bootstrapper.WorkspaceContextInitializationStep'), \
         patch('autobyteus.agent.bootstrap_steps.agent_bootstrapper.McpServerPrewarmingStep'), \
         patch('autobyteus.agent.bootstrap_steps.agent_bootstrapper.SystemPromptProcessingStep'), \
         patch('autobyteus.agent.bootstrap_steps.agent_bootstrapper.WorkingContextSnapshotRestoreStep'):
        with caplog.at_level(logging.DEBUG):
            bootstrapper = AgentBootstrapper()
        
        assert len(bootstrapper.bootstrap_steps) == 4
        assert "AgentBootstrapper initialized with default steps" in caplog.text


def test_bootstrapper_initialization_custom(mock_step_1, mock_step_2):
    """Test that the bootstrapper initializes with a custom list of steps."""
    custom_steps = [mock_step_1, mock_step_2]
    bootstrapper = AgentBootstrapper(steps=custom_steps)
    assert bootstrapper.bootstrap_steps == custom_steps
    assert len(bootstrapper.bootstrap_steps) == 2
