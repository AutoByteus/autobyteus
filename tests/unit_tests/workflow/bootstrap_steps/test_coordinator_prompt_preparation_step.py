# file: autobyteus/tests/unit_tests/workflow/bootstrap_steps/test_coordinator_prompt_preparation_step.py
import pytest
from unittest.mock import MagicMock

from autobyteus.workflow.bootstrap_steps.coordinator_prompt_preparation_step import CoordinatorPromptPreparationStep
from autobyteus.workflow.context import (
    WorkflowContext,
    WorkflowConfig,
    WorkflowNodeConfig,
)

@pytest.fixture
def prompt_prep_step():
    """Provides a clean instance of CoordinatorPromptPreparationStep."""
    return CoordinatorPromptPreparationStep()

@pytest.mark.asyncio
async def test_execute_success_with_team(
    prompt_prep_step: CoordinatorPromptPreparationStep,
    workflow_context: WorkflowContext
):
    """
    Tests successful execution for a standard team with a coordinator and one member.
    """
    success = await prompt_prep_step.execute(workflow_context, workflow_context.phase_manager)

    assert success is True
    
    prompt = workflow_context.state.prepared_coordinator_prompt
    assert isinstance(prompt, str)
    assert prompt.startswith("You are the coordinator of a team of specialist agents.")
    assert "### Goal\nA test workflow" in prompt
    assert "### Your Team\n- **Member** (Role: Member_role): Description for Member" in prompt
    assert "### Execution Rules" not in prompt
    assert "### Your Task" in prompt

@pytest.mark.asyncio
async def test_execute_with_solo_coordinator(
    prompt_prep_step: CoordinatorPromptPreparationStep,
    workflow_context: WorkflowContext
):
    """
    Tests successful execution for a workflow with only a single coordinator node.
    """
    solo_node = workflow_context.config.coordinator_node
    workflow_context.config = WorkflowConfig(
        nodes=[solo_node],
        coordinator_node=solo_node,
        description="Solo workflow"
    )

    success = await prompt_prep_step.execute(workflow_context, workflow_context.phase_manager)

    assert success is True
    prompt = workflow_context.state.prepared_coordinator_prompt
    assert prompt.startswith("You are working alone.")
    assert "### Your Team\nYou are working alone on this task." in prompt

@pytest.mark.asyncio
async def test_execute_failure_path(
    prompt_prep_step: CoordinatorPromptPreparationStep,
    workflow_context: WorkflowContext,
    monkeypatch
):
    """
    Tests the generic failure path by mocking an exception.
    """
    error_message = "Synthetic error"
    monkeypatch.setattr(
        prompt_prep_step,
        '_generate_unique_node_ids',
        MagicMock(side_effect=ValueError(error_message))
    )

    success = await prompt_prep_step.execute(workflow_context, workflow_context.phase_manager)

    assert success is False
    assert workflow_context.state.prepared_coordinator_prompt is None
