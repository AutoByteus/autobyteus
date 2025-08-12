# file: autobyteus/tests/unit_tests/agent_team/bootstrap_steps/test_agent_team_bootstrapper.py
import pytest
import logging
from unittest.mock import AsyncMock, patch

from autobyteus.agent_team.bootstrap_steps.agent_team_bootstrapper import AgentTeamBootstrapper
from autobyteus.agent_team.bootstrap_steps.base_agent_team_bootstrap_step import BaseAgentTeamBootstrapStep
from autobyteus.agent_team.events.agent_team_events import AgentTeamReadyEvent

# Dummy classes for robust spec'ing
class MockStep1(BaseAgentTeamBootstrapStep):
    async def execute(self, context, phase_manager): pass

class MockStep2(BaseAgentTeamBootstrapStep):
    async def execute(self, context, phase_manager): pass

@pytest.fixture
def mock_step_1():
    step = AsyncMock(spec=MockStep1)
    step.execute.return_value = True
    return step

@pytest.fixture
def mock_step_2():
    step = AsyncMock(spec=MockStep2)
    step.execute.return_value = True
    return step

def test_bootstrapper_initialization_default(caplog):
    """Test that the bootstrapper initializes with default steps if none are provided."""
    with patch('autobyteus.agent_team.bootstrap_steps.agent_team_bootstrapper.AgentTeamRuntimeQueueInitializationStep') as mock_q_init, \
         patch('autobyteus.agent_team.bootstrap_steps.agent_team_bootstrapper.TeamContextInitializationStep') as mock_ctx_init, \
         patch('autobyteus.agent_team.bootstrap_steps.agent_team_bootstrapper.TaskNotifierInitializationStep') as mock_notifier_init, \
         patch('autobyteus.agent_team.bootstrap_steps.agent_team_bootstrapper.CoordinatorPromptPreparationStep') as mock_prompt_prep, \
         patch('autobyteus.agent_team.bootstrap_steps.agent_team_bootstrapper.AgentToolInjectionStep') as mock_tool_inject, \
         patch('autobyteus.agent_team.bootstrap_steps.agent_team_bootstrapper.CoordinatorInitializationStep') as mock_coord_init:
        
        bootstrapper = AgentTeamBootstrapper()
        
        mock_q_init.assert_called_once()
        mock_ctx_init.assert_called_once()
        mock_notifier_init.assert_called_once()
        mock_prompt_prep.assert_called_once()
        mock_tool_inject.assert_called_once()
        mock_coord_init.assert_called_once()
        
        assert len(bootstrapper.bootstrap_steps) == 6

def test_bootstrapper_initialization_custom(mock_step_1, mock_step_2):
    """Test that the bootstrapper initializes with a custom list of steps."""
    custom_steps = [mock_step_1, mock_step_2]
    bootstrapper = AgentTeamBootstrapper(steps=custom_steps)
    assert bootstrapper.bootstrap_steps == custom_steps
    assert len(bootstrapper.bootstrap_steps) == 2

@pytest.mark.asyncio
async def test_run_success(agent_team_context, mock_step_1, mock_step_2):
    """Test a successful run where all steps pass."""
    bootstrapper = AgentTeamBootstrapper(steps=[mock_step_1, mock_step_2])
    phase_manager = agent_team_context.phase_manager
    
    success = await bootstrapper.run(agent_team_context, phase_manager)

    assert success is True
    phase_manager.notify_bootstrapping_started.assert_awaited_once()
    mock_step_1.execute.assert_awaited_once_with(agent_team_context, phase_manager)
    mock_step_2.execute.assert_awaited_once_with(agent_team_context, phase_manager)
    
    agent_team_context.state.input_event_queues.enqueue_internal_system_event.assert_awaited_once()
    enqueued_event = agent_team_context.state.input_event_queues.enqueue_internal_system_event.call_args[0][0]
    assert isinstance(enqueued_event, AgentTeamReadyEvent)
    
    phase_manager.notify_error_occurred.assert_not_awaited()

@pytest.mark.asyncio
async def test_run_fails_and_stops(agent_team_context, mock_step_1, mock_step_2):
    """Test a failed run where one step returns False, halting the process."""
    mock_step_1.execute.return_value = False
    
    bootstrapper = AgentTeamBootstrapper(steps=[mock_step_1, mock_step_2])
    phase_manager = agent_team_context.phase_manager
    
    success = await bootstrapper.run(agent_team_context, phase_manager)

    assert success is False
    phase_manager.notify_bootstrapping_started.assert_awaited_once()
    mock_step_1.execute.assert_awaited_once()
    mock_step_2.execute.assert_not_awaited()
    
    phase_manager.notify_error_occurred.assert_awaited_once()
    args, kwargs = phase_manager.notify_error_occurred.call_args
    assert "Bootstrap step MockStep1 failed." in args[0]

    agent_team_context.state.input_event_queues.enqueue_internal_system_event.assert_not_called()

@pytest.mark.asyncio
async def test_run_fails_if_queues_not_set_after_success(agent_team_context, mock_step_1):
    """Test failure if queues are not available after all steps supposedly succeeded."""
    bootstrapper = AgentTeamBootstrapper(steps=[mock_step_1])
    phase_manager = agent_team_context.phase_manager
    
    agent_team_context.state.input_event_queues = None
    
    success = await bootstrapper.run(agent_team_context, phase_manager)

    assert success is False
    phase_manager.notify_bootstrapping_started.assert_awaited_once()
    mock_step_1.execute.assert_awaited_once()
    
    phase_manager.notify_error_occurred.assert_awaited_once()
    args, kwargs = phase_manager.notify_error_occurred.call_args
    assert "Queues unavailable after bootstrap." in args[0]
