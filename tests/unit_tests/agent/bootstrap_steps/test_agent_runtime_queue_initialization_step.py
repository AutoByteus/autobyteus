# file: autobyteus/tests/unit_tests/agent/bootstrap_steps/test_agent_runtime_queue_initialization_step.py
import pytest
import logging
from unittest.mock import MagicMock, AsyncMock

# Import the class to be tested
from autobyteus.agent.bootstrap_steps.agent_runtime_queue_initialization_step import AgentRuntimeQueueInitializationStep
# Import dependent classes for type checking and mocking
from autobyteus.agent.events import AgentInputEventQueueManager, AgentErrorEvent
from autobyteus.agent.context import AgentContext
from autobyteus.agent.context.agent_phase_manager import AgentPhaseManager

# Fixture for the step instance
@pytest.fixture
def queue_init_step():
    """Provides an instance of AgentRuntimeQueueInitializationStep for testing."""
    return AgentRuntimeQueueInitializationStep(input_queue_size=10)

# Test the __init__ method
def test_queue_initialization_step_init(caplog):
    """Test that the step initializes correctly with a given input queue size."""
    with caplog.at_level(logging.DEBUG):
        step = AgentRuntimeQueueInitializationStep(input_queue_size=50)
    assert step.input_queue_size == 50
    assert "AgentRuntimeQueueInitializationStep initialized with input_q_size=50" in caplog.text

# Test successful execution when queues are not yet initialized
@pytest.mark.asyncio
async def test_execute_success_first_time(
    queue_init_step: AgentRuntimeQueueInitializationStep,
    agent_context: AgentContext,
    mock_phase_manager: AgentPhaseManager,
    caplog,
    monkeypatch
):
    """Test the successful execution path where queues are initially None."""
    # Ensure queues are None initially
    agent_context.state.input_event_queues = None
    
    # Mock the AgentInputEventQueueManager class
    mock_queue_manager_instance = MagicMock(spec=AgentInputEventQueueManager)
    # The method we might assert on is async, so it should be an AsyncMock
    mock_queue_manager_instance.enqueue_internal_system_event = AsyncMock()
    mock_queue_manager_class = MagicMock(return_value=mock_queue_manager_instance)
    
    monkeypatch.setattr(
        "autobyteus.agent.bootstrap_steps.agent_runtime_queue_initialization_step.AgentInputEventQueueManager",
        mock_queue_manager_class
    )
    
    with caplog.at_level(logging.INFO):
        success = await queue_init_step.execute(agent_context, mock_phase_manager)

    assert success is True
    assert "Executing AgentRuntimeQueueInitializationStep (for input queues)" in caplog.text
    assert "AgentInputEventQueueManager initialized and set in agent state" in caplog.text
    
    # Check that a warning about overwriting is NOT present
    assert "queues seem to be already initialized. Overwriting" not in caplog.text
    
    # Check that the class was instantiated with the correct size
    mock_queue_manager_class.assert_called_once_with(queue_size=queue_init_step.input_queue_size)
    
    # Check that the context state has been updated with the mock instance
    assert agent_context.state.input_event_queues is mock_queue_manager_instance
    
    # Check that no error event was enqueued
    mock_queue_manager_instance.enqueue_internal_system_event.assert_not_called()

# Test successful execution when queues are already initialized (overwrite scenario)
@pytest.mark.asyncio
async def test_execute_success_overwrite(
    queue_init_step: AgentRuntimeQueueInitializationStep,
    agent_context: AgentContext,
    mock_phase_manager: AgentPhaseManager,
    caplog,
    monkeypatch
):
    """Test the case where queues are already initialized and should be overwritten."""
    # Pre-set the queues to some mock object to simulate they are already initialized
    initial_queue_manager = MagicMock(spec=AgentInputEventQueueManager)
    agent_context.state.input_event_queues = initial_queue_manager

    # Mock the AgentInputEventQueueManager class for the overwrite
    mock_new_queue_manager_instance = MagicMock(spec=AgentInputEventQueueManager)
    mock_queue_manager_class = MagicMock(return_value=mock_new_queue_manager_instance)
    monkeypatch.setattr(
        "autobyteus.agent.bootstrap_steps.agent_runtime_queue_initialization_step.AgentInputEventQueueManager",
        mock_queue_manager_class
    )
    
    with caplog.at_level(logging.WARNING): # Capture WARNING and above
        success = await queue_init_step.execute(agent_context, mock_phase_manager)

    assert success is True
    
    # Check that a warning about overwriting IS present
    assert "Input runtime queues seem to be already initialized. Overwriting. This might indicate a logic error." in caplog.text
    
    # Check that the context state has been updated with a NEW instance
    assert agent_context.state.input_event_queues is mock_new_queue_manager_instance
    assert agent_context.state.input_event_queues is not initial_queue_manager

# Test failure during instantiation
@pytest.mark.asyncio
async def test_execute_failure_during_instantiation(
    queue_init_step: AgentRuntimeQueueInitializationStep,
    agent_context: AgentContext,
    mock_phase_manager: AgentPhaseManager,
    caplog,
    monkeypatch
):
    """Test the failure path where AgentInputEventQueueManager instantiation fails."""
    # Ensure queues are None initially, so we can check they remain None
    agent_context.state.input_event_queues = None
    
    exception_message = "Failed to create queues"
    # Patch the class to raise an exception upon instantiation
    monkeypatch.setattr(
        "autobyteus.agent.bootstrap_steps.agent_runtime_queue_initialization_step.AgentInputEventQueueManager",
        MagicMock(side_effect=RuntimeError(exception_message))
    )

    with caplog.at_level(logging.ERROR):
        success = await queue_init_step.execute(agent_context, mock_phase_manager)

    assert success is False
    assert f"Critical failure during AgentRuntimeQueueInitializationStep (input queues): {exception_message}" in caplog.text
    
    # Ensure queues are still None
    assert agent_context.state.input_event_queues is None

    # This part of the SUT's except block is unreachable if the queue object is None, so we assert not_called
    # on the original mock object from the conftest fixture if it were to exist.
    # However, since we set it to None, there's nothing to check for calls on, which is correct.
    # This also confirms the `if context.state.input_event_queues` check in the SUT works.
