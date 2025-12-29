# file: autobyteus/tests/unit_tests/agent_team/bootstrap_steps/test_agent_team_runtime_queue_initialization_step.py
import pytest
import logging
from unittest.mock import MagicMock

from autobyteus.agent_team.bootstrap_steps.agent_team_runtime_queue_initialization_step import AgentTeamRuntimeQueueInitializationStep
from autobyteus.agent_team.events.agent_team_input_event_queue_manager import AgentTeamInputEventQueueManager
from autobyteus.agent_team.context import AgentTeamContext
from autobyteus.agent_team.status.agent_team_status_manager import AgentTeamStatusManager

@pytest.fixture
def queue_init_step():
    """Provides a clean instance of AgentTeamRuntimeQueueInitializationStep."""
    return AgentTeamRuntimeQueueInitializationStep()

@pytest.mark.asyncio
async def test_execute_success(
    queue_init_step: AgentTeamRuntimeQueueInitializationStep,
    agent_team_context: AgentTeamContext,
    monkeypatch
):
    """
    Tests the successful execution of the step, where the queue manager
    is instantiated and attached to the agent_team context.
    """
    # Ensure the state is clean before the test
    agent_team_context.state.input_event_queues = None
    
    # Mock the class that will be instantiated
    mock_queue_manager_instance = MagicMock(spec=AgentTeamInputEventQueueManager)
    mock_queue_manager_class = MagicMock(return_value=mock_queue_manager_instance)
    
    monkeypatch.setattr(
        "autobyteus.agent_team.bootstrap_steps.agent_team_runtime_queue_initialization_step.AgentTeamInputEventQueueManager",
        mock_queue_manager_class
    )
    
    success = await queue_init_step.execute(agent_team_context, agent_team_context.status_manager)

    assert success is True
    
    # Verify the manager was instantiated
    mock_queue_manager_class.assert_called_once_with()
    
    # Verify the context state was updated with the new instance
    assert agent_team_context.state.input_event_queues is mock_queue_manager_instance

@pytest.mark.asyncio
async def test_execute_failure_on_instantiation(
    queue_init_step: AgentTeamRuntimeQueueInitializationStep,
    agent_team_context: AgentTeamContext,
    caplog,
    monkeypatch
):
    """
    Tests the failure path where instantiating AgentTeamInputEventQueueManager
    raises an exception.
    """
    agent_team_context.state.input_event_queues = None
    
    exception_message = "Failed to create agent_team queues"
    mock_queue_manager_class = MagicMock(side_effect=RuntimeError(exception_message))
    
    monkeypatch.setattr(
        "autobyteus.agent_team.bootstrap_steps.agent_team_runtime_queue_initialization_step.AgentTeamInputEventQueueManager",
        mock_queue_manager_class
    )

    with caplog.at_level(logging.ERROR):
        success = await queue_init_step.execute(agent_team_context, agent_team_context.status_manager)

    assert success is False
    
    # Check that the specific error was logged
    assert f"Critical failure during queue initialization: {exception_message}" in caplog.text
    
    # Ensure the state was not modified
    assert agent_team_context.state.input_event_queues is None
