# file: autobyteus/tests/unit_tests/agent_team/system_prompt_processor/test_team_manifest_injector_processor.py
import pytest

from autobyteus.agent.context import AgentConfig
from autobyteus.agent.context.agent_context import AgentContext
from autobyteus.agent.context.agent_runtime_state import AgentRuntimeState
from autobyteus.agent_team.context import AgentTeamConfig, TeamNodeConfig
from autobyteus.agent_team.context.agent_team_context import AgentTeamContext
from autobyteus.agent_team.context.agent_team_runtime_state import AgentTeamRuntimeState
from autobyteus.agent_team.system_prompt_processor.team_manifest_injector_processor import (
    TeamManifestInjectorProcessor,
)


def _build_team_context(team_id: str, nodes: tuple[TeamNodeConfig, ...]) -> AgentTeamContext:
    coordinator_node = nodes[0]
    team_config = AgentTeamConfig(
        name="Team",
        description="Team desc",
        nodes=nodes,
        coordinator_node=coordinator_node,
    )
    team_state = AgentTeamRuntimeState(team_id=team_id)
    return AgentTeamContext(team_id=team_id, config=team_config, state=team_state)


def _build_agent_context(agent_config: AgentConfig, team_context: AgentTeamContext | None) -> AgentContext:
    runtime_state = AgentRuntimeState(agent_id=f"agent_{agent_config.name}")
    if team_context:
        runtime_state.custom_data["team_context"] = team_context
    return AgentContext(agent_id=runtime_state.agent_id, config=agent_config, state=runtime_state)


@pytest.mark.asyncio
async def test_process_no_team_context_returns_prompt(mock_llm_instance):
    agent_config = AgentConfig(
        name="Solo",
        role="Solo_role",
        description="Solo desc",
        llm_instance=mock_llm_instance,
        system_prompt="Base prompt",
        tools=[],
    )
    agent_context = _build_agent_context(agent_config, None)

    processor = TeamManifestInjectorProcessor()
    result = processor.process("Base prompt", {}, agent_context.agent_id, agent_context)

    assert result == "Base prompt"


@pytest.mark.asyncio
async def test_process_replaces_placeholder_with_manifest(agent_config_factory):
    coordinator_def = agent_config_factory("Coordinator")
    coordinator_def.system_prompt = "Team:\n{{team}}"
    member_def = agent_config_factory("Member")
    member_def.description = "This is the member agent."

    team_context = _build_team_context(
        "team_1",
        (TeamNodeConfig(node_definition=coordinator_def), TeamNodeConfig(node_definition=member_def)),
    )

    agent_context = _build_agent_context(coordinator_def, team_context)

    processor = TeamManifestInjectorProcessor()
    result = processor.process(coordinator_def.system_prompt, {}, agent_context.agent_id, agent_context)

    assert result == "Team:\n- name: Member\n  description: This is the member agent."


@pytest.mark.asyncio
async def test_process_appends_manifest_when_missing_placeholder(agent_config_factory):
    coordinator_def = agent_config_factory("Coordinator")
    coordinator_def.system_prompt = "Base prompt"
    member_def = agent_config_factory("Member")

    team_context = _build_team_context(
        "team_2",
        (TeamNodeConfig(node_definition=coordinator_def), TeamNodeConfig(node_definition=member_def)),
    )

    agent_context = _build_agent_context(coordinator_def, team_context)

    processor = TeamManifestInjectorProcessor()
    result = processor.process(coordinator_def.system_prompt, {}, agent_context.agent_id, agent_context)

    expected_manifest = "- name: Member\n  description: Description for Member"
    assert result == "Base prompt\n\n## Team Manifest\n\n" + expected_manifest


@pytest.mark.asyncio
async def test_process_handles_solo_team(agent_config_factory):
    coordinator_def = agent_config_factory("Solo")
    coordinator_def.system_prompt = "Team: {{team}}"

    team_context = _build_team_context(
        "team_3",
        (TeamNodeConfig(node_definition=coordinator_def),),
    )

    agent_context = _build_agent_context(coordinator_def, team_context)

    processor = TeamManifestInjectorProcessor()
    result = processor.process(coordinator_def.system_prompt, {}, agent_context.agent_id, agent_context)

    assert result == "Team: You are working alone. You have no team members to delegate to."
