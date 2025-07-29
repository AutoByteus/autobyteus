# file: autobyteus/tests/unit_tests/workflow/bootstrap_steps/test_workflow_runtime_queue_initialization_step.py
import pytest
import logging
from unittest.mock import MagicMock

from autobyteus.agent.workflow.bootstrap_steps.workflow_runtime_queue_initialization_step import WorkflowRuntimeQueueInitializationStep
from autobyteus.agent.workflow.events.workflow_input_event_queue_manager import WorkflowInputEventQueueManager
from autobyteus.agent.workflow.context import WorkflowContext
from autobyteus.agent.workflow.phases.workflow_phase_manager import WorkflowPhaseManager

@pytest.fixture
def queue_init_step():
    """Provides a clean instance of WorkflowRuntimeQueueInitializationStep."""
    return WorkflowRuntimeQueueInitializationStep()

@pytest.mark.asyncio
async def test_execute_success(
    queue_init_step: WorkflowRuntimeQueueInitializationStep,
    workflow_context: WorkflowContext,
    mock_workflow_phase_manager: WorkflowPhaseManager,
    monkeypatch
):
    """
    Tests the successful execution of the step, where the queue manager
    is instantiated and attached to the workflow context.
    """
    # Ensure the state is clean before the test
    workflow_context.state.input_event_queues = None
    
    # Mock the class that will be instantiated
    mock_queue_manager_instance = MagicMock(spec=WorkflowInputEventQueueManager)
    mock_queue_manager_class = MagicMock(return_value=mock_queue_manager_instance)
    
    monkeypatch.setattr(
        "autobyteus.agent.workflow.bootstrap_steps.workflow_runtime_queue_initialization_step.WorkflowInputEventQueueManager",
        mock_queue_manager_class
    )
    
    success = await queue_init_step.execute(workflow_context, mock_workflow_phase_manager)

    assert success is True
    
    # Verify the manager was instantiated
    mock_queue_manager_class.assert_called_once_with()
    
    # Verify the context state was updated with the new instance
    assert workflow_context.state.input_event_queues is mock_queue_manager_instance

@pytest.mark.asyncio
async def test_execute_failure_on_instantiation(
    queue_init_step: WorkflowRuntimeQueueInitializationStep,
    workflow_context: WorkflowContext,
    mock_workflow_phase_manager: WorkflowPhaseManager,
    caplog,
    monkeypatch
):
    """
    Tests the failure path where instantiating WorkflowInputEventQueueManager
    raises an exception.
    """
    workflow_context.state.input_event_queues = None
    
    exception_message = "Failed to create workflow queues"
    mock_queue_manager_class = MagicMock(side_effect=RuntimeError(exception_message))
    
    monkeypatch.setattr(
        "autobyteus.agent.workflow.bootstrap_steps.workflow_runtime_queue_initialization_step.WorkflowInputEventQueueManager",
        mock_queue_manager_class
    )

    with caplog.at_level(logging.ERROR):
        success = await queue_init_step.execute(workflow_context, mock_workflow_phase_manager)

    assert success is False
    
    # Check that the specific error was logged
    assert f"Critical failure during queue initialization: {exception_message}" in caplog.text
    
    # Ensure the state was not modified
    assert workflow_context.state.input_event_queues is None
