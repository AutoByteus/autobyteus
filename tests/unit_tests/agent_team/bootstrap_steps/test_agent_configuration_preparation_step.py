# file: autobyteus/tests/unit_tests/agent_team/bootstrap_steps/test_agent_configuration_preparation_step.py
import pytest
from unittest.mock import MagicMock

from autobyteus.agent_team.bootstrap_steps.agent_configuration_preparation_step import AgentConfigurationPreparationStep
from autobyteus.agent_team.context import AgentTeamContext, AgentTeamConfig, TeamNodeConfig
from autobyteus.agent.context import AgentConfig
from autobyteus.task_management.tools import CreateTasks
from autobyteus.agent.message.send_message_to import SendMessageTo

@pytest.fixture
def config_prep_step():
    return AgentConfigurationPreparationStep()

def _rebuild_context_with_new_config(context: AgentTeamContext, new_config: AgentTeamConfig):
    """Helper to replace the config in a context."""
    context.config = new_config
    context._node_config_map = None

@pytest.mark.asyncio
async def test_execute_prepares_final_configs_correctly(
    config_prep_step: AgentConfigurationPreparationStep,
    agent_team_context: AgentTeamContext,
    agent_config_factory
):
    """
    Tests that the step correctly processes agent nodes, injects context,
    applies the coordinator prompt, and stores the final configs in the state.
    It should NOT modify the user-defined tool list.
    """
    # --- Arrange ---
    # Create agent definitions with their own specific tools
    coordinator_def = agent_config_factory("Coordinator")
    # Coordinator is explicitly given SendMessageTo by the user
    coordinator_def.tools = [CreateTasks(), SendMessageTo()]

    # This member agent is NOT given the tool and should not be able to communicate
    member_def = agent_config_factory("Member")
    member_def.tools = []
    
    coordinator_node = TeamNodeConfig(node_definition=coordinator_def)
    member_node = TeamNodeConfig(node_definition=member_def)

    # Create a mock sub-team node to ensure it gets skipped
    sub_team_node = MagicMock(spec=TeamNodeConfig)
    sub_team_node.name = "SubTeam"
    sub_team_node.is_sub_team = True
    
    # Rebuild the context with this specific configuration
    new_team_config = AgentTeamConfig(
        name="TestTeamWithExplicitTools",
        description="A test team",
        nodes=(coordinator_node, member_node, sub_team_node),
        coordinator_node=coordinator_node
    )
    _rebuild_context_with_new_config(agent_team_context, new_team_config)

    # Set up a prepared prompt for the coordinator
    prepared_prompt = "This is the special coordinator prompt."
    agent_team_context.state.prepared_coordinator_prompt = prepared_prompt

    # --- Act ---
    success = await config_prep_step.execute(agent_team_context, agent_team_context.phase_manager)

    # --- Assert ---
    assert success is True
    
    final_configs = agent_team_context.state.final_agent_configs
    # Should only contain configs for the two agents, not the sub-team
    assert len(final_configs) == 2
    
    # --- Verify Coordinator Config ---
    coord_config = final_configs.get(coordinator_node.name)
    assert coord_config is not None
    assert isinstance(coord_config, AgentConfig)
    
    # Check that original tools are preserved and NO new tools are added
    coord_tool_names = {t.get_name() for t in coord_config.tools}
    assert CreateTasks.get_name() in coord_tool_names
    assert SendMessageTo.get_name() in coord_tool_names
    assert len(coord_tool_names) == 2
    
    # Check that the special prompt was applied
    assert coord_config.system_prompt == prepared_prompt
    
    # Check that team context was injected
    assert coord_config.initial_custom_data["team_context"] is agent_team_context

    # --- Verify Member Config ---
    member_config = final_configs.get(member_node.name)
    assert member_config is not None
    assert isinstance(member_config, AgentConfig)

    # Check that the member's tool list is empty, as defined by the user
    assert len(member_config.tools) == 0

    # Check that team context was injected
    assert member_config.initial_custom_data["team_context"] is agent_team_context

@pytest.mark.asyncio
async def test_execute_fails_if_team_manager_missing(
    config_prep_step: AgentConfigurationPreparationStep,
    agent_team_context: AgentTeamContext
):
    """
    Tests that the step fails gracefully if the team manager is not in the context.
    """
    agent_team_context.state.team_manager = None
    
    success = await config_prep_step.execute(agent_team_context, agent_team_context.phase_manager)
    
    assert success is False
