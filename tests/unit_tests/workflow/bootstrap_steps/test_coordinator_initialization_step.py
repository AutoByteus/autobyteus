# file: autobyteus/tests/unit_tests/workflow/bootstrap_steps/test_coordinator_initialization_step.py
import pytest
from unittest.mock import MagicMock, AsyncMock

from autobyteus.workflow.bootstrap_steps.coordinator_initialization_step import CoordinatorInitializationStep
from autobyteus.workflow.context import WorkflowContext
from autobyteus.agent.agent import Agent

@pytest.fixture
def coord_init_step():
    return CoordinatorInitializationStep()

@pytest.mark.asyncio
async def test_execute_success(
    coord_init_step: CoordinatorInitializationStep,
    workflow_context: WorkflowContext
):
    """
    Tests that the step correctly awaits the TeamManager to get the coordinator.
    """
    mock_team_manager = workflow_context.team_manager
    mock_team_manager.ensure_coordinator_is_ready = AsyncMock(return_value=MagicMock(spec=Agent))
    coordinator_name = workflow_context.config.coordinator_node.name

    success = await coord_init_step.execute(workflow_context, workflow_context.phase_manager)

    assert success is True
    mock_team_manager.ensure_coordinator_is_ready.assert_awaited_once_with(coordinator_name)

@pytest.mark.asyncio
async def test_execute_failure_if_team_manager_missing(
    coord_init_step: CoordinatorInitializationStep,
    workflow_context: WorkflowContext
):
    """
    Tests that the step fails if the TeamManager is not available in the context.
    """
    workflow_context.state.team_manager = None

    success = await coord_init_step.execute(workflow_context, workflow_context.phase_manager)

    assert success is False

@pytest.mark.asyncio
async def test_execute_failure_if_coordinator_creation_fails(
    coord_init_step: CoordinatorInitializationStep,
    workflow_context: WorkflowContext
):
    """
    Tests that the step fails if the TeamManager's async method raises an exception.
    """
    mock_team_manager = workflow_context.team_manager
    mock_team_manager.ensure_coordinator_is_ready = AsyncMock(side_effect=ValueError("Config not found"))

    success = await coord_init_step.execute(workflow_context, workflow_context.phase_manager)

    assert success is False
