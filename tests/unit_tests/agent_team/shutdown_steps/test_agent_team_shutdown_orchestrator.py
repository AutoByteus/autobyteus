# file: autobyteus/tests/unit_tests/agent_team/shutdown_steps/test_agent_team_shutdown_orchestrator.py
import pytest
import logging
from unittest.mock import AsyncMock, patch

from autobyteus.agent_team.shutdown_steps.agent_team_shutdown_orchestrator import AgentTeamShutdownOrchestrator
from autobyteus.agent_team.shutdown_steps.base_agent_team_shutdown_step import BaseAgentTeamShutdownStep
from autobyteus.agent_team.context import AgentTeamContext

# Define dummy classes for spec'ing mocks
class MockAgentTeamShutdownStep1(BaseAgentTeamShutdownStep):
    async def execute(self, context):
        pass

class MockAgentTeamShutdownStep2(BaseAgentTeamShutdownStep):
    async def execute(self, context):
        pass

@pytest.fixture
def mock_agent_team_shutdown_step_1():
    step = AsyncMock(spec=MockAgentTeamShutdownStep1)
    step.execute.return_value = True
    return step

@pytest.fixture
def mock_agent_team_shutdown_step_2():
    step = AsyncMock(spec=MockAgentTeamShutdownStep2)
    step.execute.return_value = True
    return step

def test_orchestrator_initialization_default():
    """Test that the orchestrator initializes with default steps if none are provided."""
    with patch('autobyteus.agent_team.shutdown_steps.agent_team_shutdown_orchestrator.BridgeCleanupStep') as mock_bridge_cleanup, \
         patch('autobyteus.agent_team.shutdown_steps.agent_team_shutdown_orchestrator.SubTeamShutdownStep') as mock_sub_team_shutdown, \
         patch('autobyteus.agent_team.shutdown_steps.agent_team_shutdown_orchestrator.AgentTeamShutdownStep') as mock_agent_shutdown:
        orchestrator = AgentTeamShutdownOrchestrator()
        
        assert len(orchestrator.shutdown_steps) == 3
        mock_bridge_cleanup.assert_called_once()
        mock_sub_team_shutdown.assert_called_once()
        mock_agent_shutdown.assert_called_once()

def test_orchestrator_initialization_custom(mock_agent_team_shutdown_step_1, mock_agent_team_shutdown_step_2):
    """Test that the orchestrator initializes with a custom list of steps."""
    custom_steps = [mock_agent_team_shutdown_step_1, mock_agent_team_shutdown_step_2]
    orchestrator = AgentTeamShutdownOrchestrator(steps=custom_steps)
    assert orchestrator.shutdown_steps == custom_steps

@pytest.mark.asyncio
async def test_run_success(agent_team_context: AgentTeamContext, mock_agent_team_shutdown_step_1, mock_agent_team_shutdown_step_2):
    """Test a successful run where all shutdown steps pass."""
    orchestrator = AgentTeamShutdownOrchestrator(steps=[mock_agent_team_shutdown_step_1, mock_agent_team_shutdown_step_2])
    
    success = await orchestrator.run(agent_team_context)

    assert success is True
    mock_agent_team_shutdown_step_1.execute.assert_awaited_once_with(agent_team_context)
    mock_agent_team_shutdown_step_2.execute.assert_awaited_once_with(agent_team_context)

@pytest.mark.asyncio
async def test_run_continues_on_failure(agent_team_context: AgentTeamContext, mock_agent_team_shutdown_step_1, mock_agent_team_shutdown_step_2, caplog):
    """Test a failed run where one step returns False, but orchestration continues."""
    mock_agent_team_shutdown_step_1.execute.return_value = False
    
    orchestrator = AgentTeamShutdownOrchestrator(steps=[mock_agent_team_shutdown_step_1, mock_agent_team_shutdown_step_2])
    
    with caplog.at_level(logging.ERROR):
        success = await orchestrator.run(agent_team_context)

    assert success is False
    mock_agent_team_shutdown_step_1.execute.assert_awaited_once_with(agent_team_context)
    # The orchestrator should continue to the next step even if one fails
    mock_agent_team_shutdown_step_2.execute.assert_awaited_once_with(agent_team_context)
    assert "Shutdown step MockAgentTeamShutdownStep1 failed" in caplog.text
