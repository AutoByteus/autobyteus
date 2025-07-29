# file: autobyteus/tests/unit_tests/workflow/bootstrap_steps/test_coordinator_prompt_preparation_step.py
import pytest
from unittest.mock import MagicMock

from autobyteus.agent.workflow.bootstrap_steps.coordinator_prompt_preparation_step import CoordinatorPromptPreparationStep
from autobyteus.agent.workflow.context import (
    WorkflowContext,
    WorkflowConfig,
    WorkflowNodeConfig,
)
from autobyteus.agent.context import AgentConfig

@pytest.fixture
def prompt_prep_step():
    """Provides a clean instance of CoordinatorPromptPreparationStep."""
    return CoordinatorPromptPreparationStep()

@pytest.mark.asyncio
async def test_execute_success_with_team(
    prompt_prep_step: CoordinatorPromptPreparationStep,
    workflow_context: WorkflowContext,
    mock_workflow_phase_manager: MagicMock
):
    """
    Tests successful execution for a standard team with a coordinator and one member.
    """
    success = await prompt_prep_step.execute(workflow_context, mock_workflow_phase_manager)

    assert success is True
    
    # 1. Verify member_node_ids
    assert workflow_context.state.member_node_ids is not None
    assert len(workflow_context.state.member_node_ids) == 1
    
    member_node = next(n for n in workflow_context.config.nodes if n != workflow_context.config.coordinator_node)
    assert member_node in workflow_context.state.member_node_ids
    assert workflow_context.state.member_node_ids[member_node] == "Member"

    # 2. Verify modified_coordinator_config
    modified_config = workflow_context.state.modified_coordinator_config
    assert isinstance(modified_config, AgentConfig)
    
    # 3. Verify prompt content
    prompt = modified_config.system_prompt
    
    # The prompt should now start with a natural, role-defining sentence.
    assert prompt.startswith("You are the coordinator of a team of specialist agents.")
    
    # It should not contain the old mechanical markers.
    assert "--- WORKFLOW CONTEXT ---" not in prompt
    
    # It should contain the structured, markdown-formatted sections.
    assert "### Goal\nA test workflow" in prompt
    assert "### Your Team\n- **Member** (Role: Member_role): Description for Member" in prompt
    
    # Since there are no dependencies, the "Execution Rules" section should NOT be present.
    assert "### Execution Rules" not in prompt
    
    assert "### Your Task" in prompt

@pytest.mark.asyncio
async def test_execute_with_solo_coordinator(
    prompt_prep_step: CoordinatorPromptPreparationStep,
    workflow_context: WorkflowContext, # This context will be modified
    mock_workflow_phase_manager: MagicMock
):
    """
    Tests successful execution for a workflow with only a single coordinator node.
    """
    # Modify the context to have only one node
    solo_node = workflow_context.config.coordinator_node
    workflow_context.config = WorkflowConfig(
        nodes=[solo_node],
        coordinator_node=solo_node,
        description="Solo workflow"
    )

    success = await prompt_prep_step.execute(workflow_context, mock_workflow_phase_manager)

    assert success is True
    assert not workflow_context.state.member_node_ids  # Should be empty

    modified_config = workflow_context.state.modified_coordinator_config
    prompt = modified_config.system_prompt
    
    assert prompt.startswith("You are working alone.")
    assert "team of specialist agents" not in prompt
    assert "use the `sendmessageto` tool" not in prompt.lower()
    assert "### Your Team\nYou are working alone on this task." in prompt
    assert "use your available tools to achieve the goal" in prompt

@pytest.mark.asyncio
async def test_execute_handles_duplicate_names(
    prompt_prep_step: CoordinatorPromptPreparationStep,
    workflow_context: WorkflowContext, # This context will be modified
    workflow_node_factory,
    mock_workflow_phase_manager: MagicMock
):
    """
    Tests that unique IDs are generated for member nodes with the same name.
    """
    coordinator_node = workflow_node_factory("Coordinator")
    member_node_1 = workflow_node_factory("Writer")
    member_node_2 = workflow_node_factory("Writer") # Duplicate name
    
    workflow_context.config = WorkflowConfig(
        nodes=[coordinator_node, member_node_1, member_node_2],
        coordinator_node=coordinator_node,
        description="Duplicate name workflow"
    )

    await prompt_prep_step.execute(workflow_context, mock_workflow_phase_manager)

    id_map = workflow_context.state.member_node_ids
    generated_ids = sorted(id_map.values()) # Sort for predictable order
    
    assert len(generated_ids) == 2
    assert generated_ids == ["Writer", "Writer_2"]

    prompt = workflow_context.state.modified_coordinator_config.system_prompt
    assert "- **Writer**" in prompt
    assert "- **Writer_2**" in prompt

@pytest.mark.asyncio
async def test_execute_generates_dependency_rules(
    prompt_prep_step: CoordinatorPromptPreparationStep,
    workflow_context: WorkflowContext, # This context will be modified
    workflow_node_factory,
    mock_workflow_phase_manager: MagicMock
):
    """
    Tests that dependency rules are correctly generated in the system prompt.
    """
    coordinator_node = workflow_node_factory("Coordinator")
    researcher_node = workflow_node_factory("Researcher")
    writer_node = WorkflowNodeConfig(
        agent_config=researcher_node.agent_config, # Reuse config for simplicity
        dependencies=[researcher_node] # writer depends on researcher
    )
    # Must override the name since we reused the config
    writer_node.agent_config.name = "Writer" 

    workflow_context.config = WorkflowConfig(
        nodes=[coordinator_node, researcher_node, writer_node],
        coordinator_node=coordinator_node,
        description="Dependency workflow"
    )

    await prompt_prep_step.execute(workflow_context, mock_workflow_phase_manager)
    
    prompt = workflow_context.state.modified_coordinator_config.system_prompt
    
    assert "### Execution Rules" in prompt
    assert "To use 'Writer', you must have already successfully used: `Researcher`." in prompt

@pytest.mark.asyncio
async def test_execute_failure_path(
    prompt_prep_step: CoordinatorPromptPreparationStep,
    workflow_context: WorkflowContext,
    mock_workflow_phase_manager: MagicMock,
    monkeypatch
):
    """
    Tests the generic failure path by mocking an exception.
    """
    # Mock a function inside the step to raise an error
    error_message = "Synthetic error"
    monkeypatch.setattr(
        prompt_prep_step,
        '_generate_unique_node_ids',
        MagicMock(side_effect=ValueError(error_message))
    )

    success = await prompt_prep_step.execute(workflow_context, mock_workflow_phase_manager)

    assert success is False
    # Verify state was not modified
    assert workflow_context.state.modified_coordinator_config is None
    assert not workflow_context.state.member_node_ids
