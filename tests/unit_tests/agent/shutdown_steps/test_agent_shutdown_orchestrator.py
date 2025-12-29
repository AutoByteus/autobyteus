# file: autobyteus/tests/unit_tests/agent/shutdown_steps/test_agent_shutdown_orchestrator.py
import pytest
import logging
from unittest.mock import MagicMock, AsyncMock, patch

from autobyteus.agent.shutdown_steps.agent_shutdown_orchestrator import AgentShutdownOrchestrator
from autobyteus.agent.shutdown_steps.base_shutdown_step import BaseShutdownStep
from autobyteus.agent.context import AgentContext

# Define dummy classes for spec'ing mocks, similar to bootstrap tests.
class MockShutdownStep1(BaseShutdownStep):
    async def execute(self, context):
        pass

class MockShutdownStep2(BaseShutdownStep):
    async def execute(self, context):
        pass

@pytest.fixture
def mock_shutdown_step_1():
    step = AsyncMock(spec=MockShutdownStep1)
    step.execute.return_value = True
    return step

@pytest.fixture
def mock_shutdown_step_2():
    step = AsyncMock(spec=MockShutdownStep2)
    step.execute.return_value = True
    return step

def test_orchestrator_initialization_default(caplog):
    """Test that the orchestrator initializes with default steps if none are provided."""
    with patch('autobyteus.agent.shutdown_steps.agent_shutdown_orchestrator.LLMInstanceCleanupStep'), \
         patch('autobyteus.agent.shutdown_steps.agent_shutdown_orchestrator.McpServerCleanupStep'):
        with caplog.at_level(logging.DEBUG):
            orchestrator = AgentShutdownOrchestrator()
        
        assert len(orchestrator.shutdown_steps) == 3
        assert "AgentShutdownOrchestrator initialized with default steps" in caplog.text

def test_orchestrator_initialization_custom(mock_shutdown_step_1, mock_shutdown_step_2):
    """Test that the orchestrator initializes with a custom list of steps."""
    custom_steps = [mock_shutdown_step_1, mock_shutdown_step_2]
    orchestrator = AgentShutdownOrchestrator(steps=custom_steps)
    assert orchestrator.shutdown_steps == custom_steps
    assert len(orchestrator.shutdown_steps) == 2

@pytest.mark.asyncio
async def test_run_success(agent_context: AgentContext, mock_shutdown_step_1, mock_shutdown_step_2):
    """Test a successful run where all shutdown steps pass."""
    orchestrator = AgentShutdownOrchestrator(steps=[mock_shutdown_step_1, mock_shutdown_step_2])
    
    success = await orchestrator.run(agent_context)

    assert success is True
    mock_shutdown_step_1.execute.assert_awaited_once_with(agent_context)
    mock_shutdown_step_2.execute.assert_awaited_once_with(agent_context)

@pytest.mark.asyncio
async def test_run_fails_and_stops(agent_context: AgentContext, mock_shutdown_step_1, mock_shutdown_step_2):
    """Test a failed run where one step returns False, halting the process."""
    mock_shutdown_step_1.execute.return_value = False  # First step fails
    
    orchestrator = AgentShutdownOrchestrator(steps=[mock_shutdown_step_1, mock_shutdown_step_2])
    
    success = await orchestrator.run(agent_context)

    assert success is False
    mock_shutdown_step_1.execute.assert_awaited_once()
    mock_shutdown_step_2.execute.assert_not_awaited()  # Second step should not be executed.
