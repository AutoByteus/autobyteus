# file: autobyteus/tests/unit_tests/agent_team/bootstrap_steps/test_coordinator_prompt_preparation_step.py
import pytest
from unittest.mock import MagicMock

from autobyteus.agent_team.bootstrap_steps.team_manifest_injection_step import TeamManifestInjectionStep
from autobyteus.agent_team.context import (
    AgentTeamContext,
    AgentTeamConfig,
    TeamNodeConfig,
)
from autobyteus.agent.context import AgentConfig


@pytest.fixture
def prompt_prep_step():
    """Provides a clean instance of TeamManifestInjectionStep."""
    return TeamManifestInjectionStep()


def _rebuild_context_with_new_config(context: AgentTeamContext, new_config: AgentTeamConfig):
    """Helper to replace the config in a context."""
    context.config = new_config
    context._node_config_map = None


@pytest.mark.asyncio
async def test_execute_injects_manifest_for_each_agent(
    prompt_prep_step: TeamManifestInjectionStep,
    agent_team_context: AgentTeamContext,
    agent_config_factory
):
    """
    Each agent with a {{team}} placeholder receives a manifest that excludes itself.
    """
    coordinator_def = agent_config_factory("Coordinator")
    coordinator_def.system_prompt = "Team Manifest:\n{{team}}"

    member_def = agent_config_factory("Member")
    member_def.system_prompt = "Known team:\n{{team}}"
    member_def.description = "This is the member agent."

    coordinator_node = TeamNodeConfig(node_definition=coordinator_def)
    member_node = TeamNodeConfig(node_definition=member_def)

    new_team_config = AgentTeamConfig(
        name="Team",
        description="desc",
        nodes=(coordinator_node, member_node),
        coordinator_node=coordinator_node
    )
    _rebuild_context_with_new_config(agent_team_context, new_team_config)

    success = await prompt_prep_step.execute(agent_team_context)

    assert success is True
    prompts = agent_team_context.state.prepared_agent_prompts
    # Coordinator should see the member
    assert prompts[coordinator_node.name] == "Team Manifest:\n- name: Member\n  description: This is the member agent."
    # Member should see the coordinator with the coordinator's description from the factory
    expected_member_view = f"Known team:\n- name: Coordinator\n  description: {coordinator_def.description}"
    assert prompts[member_node.name] == expected_member_view


@pytest.mark.asyncio
async def test_execute_handles_solo_agent(
    prompt_prep_step: TeamManifestInjectionStep,
    agent_team_context: AgentTeamContext,
    agent_config_factory
):
    """Solo agent gets the 'working alone' text."""
    coordinator_def = agent_config_factory("Solo")
    coordinator_def.system_prompt = "My Team: {{team}}"
    coordinator_node = TeamNodeConfig(node_definition=coordinator_def)

    solo_config = AgentTeamConfig(
        name="Solo Team",
        nodes=(coordinator_node,),
        coordinator_node=coordinator_node,
        description="Solo agent team"
    )
    _rebuild_context_with_new_config(agent_team_context, solo_config)

    success = await prompt_prep_step.execute(agent_team_context)

    assert success is True
    prompts = agent_team_context.state.prepared_agent_prompts
    assert prompts["Solo"] == "My Team: You are working alone. You have no team members to delegate to."


@pytest.mark.asyncio
async def test_execute_failure_path(
    prompt_prep_step: TeamManifestInjectionStep,
    agent_team_context: AgentTeamContext,
    monkeypatch,
    agent_config_factory
):
    """Failure during manifest generation returns False and leaves prompts empty."""
    coordinator_def = agent_config_factory("Coordinator")
    coordinator_def.system_prompt = "{{team}}"
    coordinator_node = TeamNodeConfig(node_definition=coordinator_def)
    new_config = AgentTeamConfig("FailTeam", "Desc", (coordinator_node,), coordinator_node)
    _rebuild_context_with_new_config(agent_team_context, new_config)

    monkeypatch.setattr(
        prompt_prep_step,
        '_generate_team_manifest',
        MagicMock(side_effect=ValueError("Synthetic error"))
    )

    success = await prompt_prep_step.execute(agent_team_context)

    assert success is False
    assert agent_team_context.state.prepared_agent_prompts == {}
