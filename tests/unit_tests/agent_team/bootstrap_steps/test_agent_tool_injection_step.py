# file: autobyteus/tests/unit_tests/agent_team/bootstrap_steps/test_agent_tool_injection_step.py
import pytest
from unittest.mock import MagicMock

from autobyteus.agent_team.bootstrap_steps.agent_tool_injection_step import AgentToolInjectionStep
from autobyteus.agent_team.context import AgentTeamContext, AgentTeamConfig, TeamNodeConfig
from autobyteus.agent.context import AgentConfig
from autobyteus.task_management.tools import PublishTaskPlan, UpdateTaskStatus
from autobyteus.agent.message.send_message_to import SendMessageTo

@pytest.fixture
def tool_injection_step():
    return AgentToolInjectionStep()

def _rebuild_context_with_new_config(context: AgentTeamContext, new_config: AgentTeamConfig):
    """Helper to replace the config in a context."""
    context.config = new_config
    context._node_config_map = None

@pytest.mark.asyncio
async def test_execute_prepares_final_configs(
    tool_injection_step: AgentToolInjectionStep,
    agent_team_context: AgentTeamContext,
    agent_config_factory
):
    """
    Tests that the step correctly processes agent nodes, injects tools,
    and stores the final configs in the runtime state.
    """
    # --- Arrange ---
    # Create agent definitions with their own specific tools
    coordinator_def = agent_config_factory("Coordinator")
    coordinator_def.tools = [PublishTaskPlan()] # Coordinator starts with its own tool

    member_def = agent_config_factory("Member")
    member_def.tools = [UpdateTaskStatus()] # Member starts with its own tool
    
    coordinator_node = TeamNodeConfig(node_definition=coordinator_def)
    member_node = TeamNodeConfig(node_definition=member_def)

    # Create a mock sub-team node to ensure it gets skipped
    sub_team_node = MagicMock(spec=TeamNodeConfig)
    sub_team_node.name = "SubTeam"
    sub_team_node.is_sub_team = True
    
    # Rebuild the context with this specific configuration
    new_team_config = AgentTeamConfig(
        name="TestTeamWithTools",
        description="A test team",
        nodes=(coordinator_node, member_node, sub_team_node),
        coordinator_node=coordinator_node
    )
    _rebuild_context_with_new_config(agent_team_context, new_team_config)

    # Set up a prepared prompt for the coordinator
    prepared_prompt = "This is the special coordinator prompt."
    agent_team_context.state.prepared_coordinator_prompt = prepared_prompt

    # --- Act ---
    success = await tool_injection_step.execute(agent_team_context, agent_team_context.phase_manager)

    # --- Assert ---
    assert success is True
    
    final_configs = agent_team_context.state.final_agent_configs
    # Should only contain configs for the two agents, not the sub-team
    assert len(final_configs) == 2
    
    # --- Verify Coordinator Config ---
    coord_config = final_configs.get(coordinator_node.name)
    assert coord_config is not None
    assert isinstance(coord_config, AgentConfig)
    
    # Check that original tools are preserved and SendMessageTo is added
    coord_tool_names = {t.get_name() for t in coord_config.tools}
    assert PublishTaskPlan.get_name() in coord_tool_names
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

    # Check that original tools are preserved and SendMessageTo is added
    member_tool_names = {t.get_name() for t in member_config.tools}
    assert UpdateTaskStatus.get_name() in member_tool_names
    assert SendMessageTo.get_name() in member_tool_names
    assert len(member_tool_names) == 2

    # Check that team context was injected
    assert member_config.initial_custom_data["team_context"] is agent_team_context

@pytest.mark.asyncio
async def test_execute_fails_if_team_manager_missing(
    tool_injection_step: AgentToolInjectionStep,
    agent_team_context: AgentTeamContext
):
    """
    Tests that the step fails gracefully if the team manager is not in the context.
    """
    agent_team_context.state.team_manager = None
    
    success = await tool_injection_step.execute(agent_team_context, agent_team_context.phase_manager)
    
    assert success is False
