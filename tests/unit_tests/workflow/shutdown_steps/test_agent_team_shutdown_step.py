# file: autobyteus/tests/unit_tests/workflow/shutdown_steps/test_agent_team_shutdown_step.py
import asyncio
import pytest
import logging
from unittest.mock import MagicMock, AsyncMock

from autobyteus.workflow.shutdown_steps.agent_team_shutdown_step import AgentTeamShutdownStep
from autobyteus.workflow.context import WorkflowContext

@pytest.fixture
def team_shutdown_step():
    """Provides a clean instance of AgentTeamShutdownStep."""
    return AgentTeamShutdownStep()

@pytest.mark.asyncio
async def test_execute_success_with_running_agents(
    team_shutdown_step: AgentTeamShutdownStep,
    workflow_context: WorkflowContext,
    mock_agent
):
    """
    Tests that the step successfully stops all running agents.
    """
    mock_agent.is_running = True
    mock_agent.agent_id = "running_agent_1"
    
    non_running_agent = MagicMock()
    non_running_agent.is_running = False
    
    mock_team_manager = workflow_context.team_manager
    mock_team_manager.get_all_agents.return_value = [mock_agent, non_running_agent]
    
    success = await team_shutdown_step.execute(workflow_context)
    
    assert success is True
    mock_agent.stop.assert_awaited_once_with(timeout=10.0)
    non_running_agent.stop.assert_not_called()

@pytest.mark.asyncio
async def test_execute_success_with_no_running_agents(
    team_shutdown_step: AgentTeamShutdownStep,
    workflow_context: WorkflowContext,
    caplog
):
    """
    Tests graceful success when no agents are running.
    """
    mock_team_manager = workflow_context.team_manager
    mock_team_manager.get_all_agents.return_value = []
    
    with caplog.at_level(logging.INFO):
        success = await team_shutdown_step.execute(workflow_context)
        
    assert success is True
    assert "No running agents to shut down" in caplog.text

@pytest.mark.asyncio
async def test_execute_success_with_no_team_manager(
    team_shutdown_step: AgentTeamShutdownStep,
    workflow_context: WorkflowContext,
    caplog
):
    """
    Tests graceful success when the team manager is not present in the context.
    """
    workflow_context.state.team_manager = None
    
    with caplog.at_level(logging.WARNING):
        success = await team_shutdown_step.execute(workflow_context)
        
    assert success is True
    assert "No TeamManager found, cannot shut down agents" in caplog.text

@pytest.mark.asyncio
async def test_execute_failure_on_agent_stop_exception(
    team_shutdown_step: AgentTeamShutdownStep,
    workflow_context: WorkflowContext,
    caplog
):
    """
    Tests that the step reports failure if an agent's stop method fails,
    but still attempts to stop other agents.
    """
    agent1 = MagicMock()
    agent1.is_running = True
    agent1.agent_id = "agent_ok"
    agent1.stop = AsyncMock()

    agent2 = MagicMock()
    agent2.is_running = True
    agent2.agent_id = "agent_fail"
    agent2.stop = AsyncMock(side_effect=RuntimeError("Stop failed"))

    mock_team_manager = workflow_context.team_manager
    mock_team_manager.get_all_agents.return_value = [agent1, agent2]
    
    with caplog.at_level(logging.ERROR):
        success = await team_shutdown_step.execute(workflow_context)

    assert success is False
    
    # Check that both stop methods were awaited despite the failure
    agent1.stop.assert_awaited_once()
    agent2.stop.assert_awaited_once()
    
    assert "Error stopping agent 'agent_fail': Stop failed" in caplog.text
