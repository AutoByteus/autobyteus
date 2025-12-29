# file: autobyteus/tests/unit_tests/agent/bootstrap_steps/test_agent_bootstrapper.py
import pytest
import logging
from unittest.mock import MagicMock, AsyncMock, patch

from autobyteus.agent.bootstrap_steps.agent_bootstrapper import AgentBootstrapper
from autobyteus.agent.bootstrap_steps.base_bootstrap_step import BaseBootstrapStep
from autobyteus.agent.context import AgentContext
from autobyteus.agent.status.manager import AgentStatusManager
from autobyteus.agent.events import AgentReadyEvent

# Define dummy classes for spec'ing mocks. This is more robust than
# manually assigning __class__.__name__.
class MockStep1(BaseBootstrapStep):
    async def execute(self, context, status_manager):
        # This method will be mocked by AsyncMock anyway, so its content doesn't matter.
        pass

class MockStep2(BaseBootstrapStep):
    async def execute(self, context, status_manager):
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
    with patch('autobyteus.agent.bootstrap_steps.agent_bootstrapper.AgentRuntimeQueueInitializationStep'), \
         patch('autobyteus.agent.bootstrap_steps.agent_bootstrapper.WorkspaceContextInitializationStep'), \
         patch('autobyteus.agent.bootstrap_steps.agent_bootstrapper.McpServerPrewarmingStep'), \
         patch('autobyteus.agent.bootstrap_steps.agent_bootstrapper.SystemPromptProcessingStep'):
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

@pytest.mark.asyncio
async def test_run_success(agent_context, mock_step_1, mock_step_2):
    """Test a successful run where all steps pass."""
    bootstrapper = AgentBootstrapper(steps=[mock_step_1, mock_step_2])
    
    success = await bootstrapper.run(agent_context, agent_context.status_manager)

    assert success is True
    agent_context.status_manager.notify_bootstrapping_started.assert_awaited_once()
    mock_step_1.execute.assert_awaited_once_with(agent_context, agent_context.status_manager)
    mock_step_2.execute.assert_awaited_once_with(agent_context, agent_context.status_manager)
    
    # Verify AgentReadyEvent was enqueued
    agent_context.state.input_event_queues.enqueue_internal_system_event.assert_awaited_once()
    enqueued_event = agent_context.state.input_event_queues.enqueue_internal_system_event.call_args[0][0]
    assert isinstance(enqueued_event, AgentReadyEvent)
    
    # Verify no error was notified
    agent_context.status_manager.notify_error_occurred.assert_not_awaited()

@pytest.mark.asyncio
async def test_run_fails_and_stops(agent_context, mock_step_1, mock_step_2):
    """Test a failed run where one step returns False, halting the process."""
    mock_step_1.execute.return_value = False # First step fails
    
    bootstrapper = AgentBootstrapper(steps=[mock_step_1, mock_step_2])
    
    success = await bootstrapper.run(agent_context, agent_context.status_manager)

    assert success is False
    agent_context.status_manager.notify_bootstrapping_started.assert_awaited_once()
    mock_step_1.execute.assert_awaited_once()
    mock_step_2.execute.assert_not_awaited() # Second step should not be executed
    
    # Verify error was notified
    agent_context.status_manager.notify_error_occurred.assert_awaited_once()
    call_kwargs = agent_context.status_manager.notify_error_occurred.call_args.kwargs
    # This assertion should now correctly pass
    assert "Critical bootstrap failure at MockStep1" in call_kwargs['error_message']

    # Verify AgentReadyEvent was NOT enqueued
    agent_context.state.input_event_queues.enqueue_internal_system_event.assert_not_called()

@pytest.mark.asyncio
async def test_run_fails_if_queues_not_set_after_success(agent_context, mock_step_1):
    """Test failure if queues are not available after all steps supposedly succeeded."""
    bootstrapper = AgentBootstrapper(steps=[mock_step_1])
    
    # Simulate steps succeeding but queues not being set
    agent_context.state.input_event_queues = None
    
    success = await bootstrapper.run(agent_context, agent_context.status_manager)

    assert success is False
    agent_context.status_manager.notify_bootstrapping_started.assert_awaited_once()
    mock_step_1.execute.assert_awaited_once()
    
    # Verify error was notified for this specific critical failure
    agent_context.status_manager.notify_error_occurred.assert_awaited_once()
    call_kwargs = agent_context.status_manager.notify_error_occurred.call_args.kwargs
    assert "Input queues unavailable after bootstrap" in call_kwargs['error_message']
