# file: autobyteus/tests/unit_tests/agent_team/bootstrap_steps/test_coordinator_prompt_preparation_step.py
import pytest
from unittest.mock import MagicMock

from autobyteus.agent_team.bootstrap_steps.coordinator_prompt_preparation_step import CoordinatorPromptPreparationStep
from autobyteus.agent_team.context import (
    AgentTeamContext,
    AgentTeamConfig,
    TeamNodeConfig,
)
from autobyteus.agent.context import AgentConfig

@pytest.fixture
def prompt_prep_step():
    """Provides a clean instance of CoordinatorPromptPreparationStep."""
    return CoordinatorPromptPreparationStep()

def _rebuild_context_with_new_config(context: AgentTeamContext, new_config: AgentTeamConfig):
    """Helper to replace the config in a context."""
    context.config = new_config
    # Invalidate the node config map cache
    context._node_config_map = None

@pytest.mark.asyncio
async def test_execute_success_with_team(
    prompt_prep_step: CoordinatorPromptPreparationStep,
    agent_team_context: AgentTeamContext,
    agent_config_factory
):
    """
    Tests successful execution where the team manifest is injected into the prompt.
    """
    # Arrange
    # Rebuild context with a coordinator that has a system prompt template
    original_config = agent_team_context.config
    coordinator_def = agent_config_factory("Coordinator")
    coordinator_def.system_prompt = "Team Manifest:\n{{team}}"

    member_def = agent_config_factory("Member")
    member_def.description = "This is the member agent."

    coordinator_node = TeamNodeConfig(node_definition=coordinator_def)
    member_node = TeamNodeConfig(node_definition=member_def)

    new_team_config = AgentTeamConfig(
        name=original_config.name,
        description=original_config.description,
        nodes=(coordinator_node, member_node),
        coordinator_node=coordinator_node
    )
    _rebuild_context_with_new_config(agent_team_context, new_team_config)

    # Act
    success = await prompt_prep_step.execute(agent_team_context, agent_team_context.phase_manager)

    # Assert
    assert success is True
    prompt = agent_team_context.state.prepared_coordinator_prompt
    expected_prompt = "Team Manifest:\n- name: Member\n  description: This is the member agent."
    assert prompt == expected_prompt

@pytest.mark.asyncio
async def test_execute_with_solo_coordinator(
    prompt_prep_step: CoordinatorPromptPreparationStep,
    agent_team_context: AgentTeamContext,
    agent_config_factory
):
    """
    Tests successful execution for a team with only a single coordinator node.
    """
    # Arrange
    coordinator_def = agent_config_factory("Coordinator")
    coordinator_def.system_prompt = "My Team: {{team}}"
    coordinator_node = TeamNodeConfig(node_definition=coordinator_def)
    
    solo_config = AgentTeamConfig(
        name="Solo Team",
        nodes=(coordinator_node,),
        coordinator_node=coordinator_node,
        description="Solo agent team"
    )
    _rebuild_context_with_new_config(agent_team_context, solo_config)

    # Act
    success = await prompt_prep_step.execute(agent_team_context, agent_team_context.phase_manager)

    # Assert
    assert success is True
    prompt = agent_team_context.state.prepared_coordinator_prompt
    assert "You are working alone. You have no team members to delegate to." in prompt
    assert prompt == "My Team: You are working alone. You have no team members to delegate to."

@pytest.mark.asyncio
async def test_execute_failure_path(
    prompt_prep_step: CoordinatorPromptPreparationStep,
    agent_team_context: AgentTeamContext,
    monkeypatch,
    agent_config_factory
):
    """
    Tests the generic failure path by mocking an exception during manifest generation.
    """
    # Arrange
    # Setup a context with a prompt to ensure the generation step is called
    coordinator_def = agent_config_factory("Coordinator")
    coordinator_def.system_prompt = "{{team}}"
    coordinator_node = TeamNodeConfig(node_definition=coordinator_def)
    new_config = AgentTeamConfig("FailTeam", "Desc", (coordinator_node,), coordinator_node)
    _rebuild_context_with_new_config(agent_team_context, new_config)
    
    error_message = "Synthetic error"
    monkeypatch.setattr(
        prompt_prep_step,
        '_generate_team_manifest',
        MagicMock(side_effect=ValueError(error_message))
    )

    # Act
    success = await prompt_prep_step.execute(agent_team_context, agent_team_context.phase_manager)

    # Assert
    assert success is False
    assert agent_team_context.state.prepared_coordinator_prompt is None
