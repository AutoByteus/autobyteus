# file: autobyteus/tests/unit_tests/agent/bootstrap_steps/test_agent_runtime_queue_initialization_step.py
import pytest
import logging
from unittest.mock import MagicMock, AsyncMock

# Import the class to be tested
from autobyteus.agent.bootstrap_steps.agent_runtime_queue_initialization_step import AgentRuntimeQueueInitializationStep
# Import dependent classes for type checking and mocking
from autobyteus.agent.events import AgentInputEventQueueManager
from autobyteus.agent.context import AgentContext
from autobyteus.agent.status.manager import AgentStatusManager

@pytest.fixture
def queue_init_step():
    """Provides an instance of AgentRuntimeQueueInitializationStep for testing."""
    return AgentRuntimeQueueInitializationStep(input_queue_size=10)

def test_queue_initialization_step_init(caplog):
    """Test that the step initializes correctly with a given input queue size."""
    with caplog.at_level(logging.DEBUG):
        step = AgentRuntimeQueueInitializationStep(input_queue_size=50)
    assert step.input_queue_size == 50
    assert "AgentRuntimeQueueInitializationStep initialized with input_q_size=50" in caplog.text

@pytest.mark.asyncio
async def test_execute_success_first_time(
    queue_init_step: AgentRuntimeQueueInitializationStep,
    agent_context: AgentContext,
    monkeypatch
):
    """Test the successful execution path where queues are initially None."""
    # This test uses the main agent_context fixture but ensures the relevant part is None
    agent_context.state.input_event_queues = None
    
    mock_queue_manager_instance = MagicMock(spec=AgentInputEventQueueManager)
    mock_queue_manager_class = MagicMock(return_value=mock_queue_manager_instance)
    
    monkeypatch.setattr(
        "autobyteus.agent.bootstrap_steps.agent_runtime_queue_initialization_step.AgentInputEventQueueManager",
        mock_queue_manager_class
    )
    
    success = await queue_init_step.execute(agent_context, agent_context.status_manager)

    assert success is True
    
    # Check that the class was instantiated with the correct size
    mock_queue_manager_class.assert_called_once_with(queue_size=queue_init_step.input_queue_size)
    
    # Check that the context state has been updated with the mock instance
    assert agent_context.state.input_event_queues is mock_queue_manager_instance

@pytest.mark.asyncio
async def test_execute_success_overwrite(
    queue_init_step: AgentRuntimeQueueInitializationStep,
    agent_context: AgentContext,
    caplog,
    monkeypatch
):
    """Test the case where queues are already initialized and should be overwritten."""
    initial_queue_manager = MagicMock(spec=AgentInputEventQueueManager)
    agent_context.state.input_event_queues = initial_queue_manager

    mock_new_queue_manager_instance = MagicMock(spec=AgentInputEventQueueManager)
    mock_queue_manager_class = MagicMock(return_value=mock_new_queue_manager_instance)
    monkeypatch.setattr(
        "autobyteus.agent.bootstrap_steps.agent_runtime_queue_initialization_step.AgentInputEventQueueManager",
        mock_queue_manager_class
    )
    
    with caplog.at_level(logging.WARNING):
        success = await queue_init_step.execute(agent_context, agent_context.status_manager)

    assert success is True
    
    assert "Input runtime queues seem to be already initialized. Overwriting." in caplog.text
    assert agent_context.state.input_event_queues is mock_new_queue_manager_instance
    assert agent_context.state.input_event_queues is not initial_queue_manager

@pytest.mark.asyncio
async def test_execute_failure_during_instantiation(
    queue_init_step: AgentRuntimeQueueInitializationStep,
    agent_context: AgentContext,
    caplog,
    monkeypatch
):
    """Test the failure path where AgentInputEventQueueManager instantiation fails."""
    agent_context.state.input_event_queues = None
    
    exception_message = "Failed to create queues"
    monkeypatch.setattr(
        "autobyteus.agent.bootstrap_steps.agent_runtime_queue_initialization_step.AgentInputEventQueueManager",
        MagicMock(side_effect=RuntimeError(exception_message))
    )

    with caplog.at_level(logging.ERROR):
        success = await queue_init_step.execute(agent_context, agent_context.status_manager)

    assert success is False
    assert f"Critical failure during AgentRuntimeQueueInitializationStep (input queues): {exception_message}" in caplog.text
    
    assert agent_context.state.input_event_queues is None
