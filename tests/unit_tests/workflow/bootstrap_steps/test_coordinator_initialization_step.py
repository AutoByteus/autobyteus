# file: autobyteus/tests/unit_tests/workflow/bootstrap_steps/test_coordinator_initialization_step.py
import pytest
from unittest.mock import MagicMock

from autobyteus.workflow.bootstrap_steps.coordinator_initialization_step import CoordinatorInitializationStep
from autobyteus.workflow.context import WorkflowContext

@pytest.fixture
def coord_init_step():
    return CoordinatorInitializationStep()

@pytest.mark.asyncio
async def test_execute_success(
    coord_init_step: CoordinatorInitializationStep,
    workflow_context: WorkflowContext,
    mock_workflow_phase_manager: MagicMock
):
    """
    Tests that the step correctly calls the TeamManager to create the coordinator.
    """
    # --- Setup ---
    mock_team_manager = workflow_context.team_manager
    coordinator_name = workflow_context.config.coordinator_node.name

    # --- Execute ---
    success = await coord_init_step.execute(workflow_context, mock_workflow_phase_manager)

    # --- Assert ---
    assert success is True
    
    # Verify the core logic: that the team manager was asked to create the coordinator
    mock_team_manager.get_and_configure_coordinator.assert_called_once_with(coordinator_name)

@pytest.mark.asyncio
async def test_execute_failure_if_team_manager_missing(
    coord_init_step: CoordinatorInitializationStep,
    workflow_context: WorkflowContext,
    mock_workflow_phase_manager: MagicMock
):
    """
    Tests that the step fails if the TeamManager is not available in the context.
    """
    workflow_context.state.team_manager = None

    success = await coord_init_step.execute(workflow_context, mock_workflow_phase_manager)

    assert success is False

@pytest.mark.asyncio
async def test_execute_failure_if_coordinator_creation_fails(
    coord_init_step: CoordinatorInitializationStep,
    workflow_context: WorkflowContext,
    mock_workflow_phase_manager: MagicMock
):
    """
    Tests that the step fails if the TeamManager raises an exception during coordinator creation.
    """
    mock_team_manager = workflow_context.team_manager
    mock_team_manager.get_and_configure_coordinator.side_effect = ValueError("Config not found")

    success = await coord_init_step.execute(workflow_context, mock_workflow_phase_manager)

    assert success is False
