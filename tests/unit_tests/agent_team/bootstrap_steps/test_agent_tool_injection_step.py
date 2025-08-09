# file: autobyteus/tests/unit_tests/agent_team/bootstrap_steps/test_agent_tool_injection_step.py
import pytest
from unittest.mock import MagicMock

from autobyteus.agent_team.bootstrap_steps.agent_tool_injection_step import AgentToolInjectionStep
from autobyteus.agent_team.context import AgentTeamContext, AgentTeamConfig
from autobyteus.agent.context import AgentConfig
from autobyteus.task_management.tools import PublishTaskPlan, UpdateTaskStatus

@pytest.fixture
def tool_injection_step():
    return AgentToolInjectionStep()

@pytest.mark.asyncio
async def test_execute_prepares_final_configs(
    tool_injection_step: AgentToolInjectionStep,
    agent_team_context: AgentTeamContext
):
    """
    Tests that the step correctly processes agent nodes, injects tools,
    and stores the final configs in the runtime state.
    """
    # --- Arrange ---
    
    # Create a mock sub-team node to ensure it gets skipped
    sub_team_node = MagicMock()
    sub_team_node.is_sub_team = True
    
    # THE FIX: Instead of modifying the frozen config, we create a new one
    # for this specific test case with the structure we need.
    original_config = agent_team_context.config
    new_nodes_tuple = original_config.nodes + (sub_team_node,)
    
    # Create a new, unfrozen config object for the test's purpose
    test_specific_config = AgentTeamConfig(
        name=original_config.name,
        description=original_config.description,
        nodes=new_nodes_tuple,
        coordinator_node=original_config.coordinator_node,
        role=original_config.role
    )
    # Now, we replace the config object on the context itself.
    agent_team_context.config = test_specific_config

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
    coordinator_name = agent_team_context.config.coordinator_node.name
    coord_config = final_configs.get(coordinator_name)
    assert coord_config is not None
    assert isinstance(coord_config, AgentConfig)
    
    # Check for coordinator-specific tools
    coord_tool_names = {t.get_name() for t in coord_config.tools}
    assert PublishTaskPlan.get_name() in coord_tool_names
    assert UpdateTaskStatus.get_name() not in coord_tool_names # Should not have member tools
    
    # Check that the special prompt was applied
    assert coord_config.system_prompt == prepared_prompt

    # --- Verify Member Config ---
    member_node = next(n for n in agent_team_context.config.nodes if n.name != coordinator_name and not n.is_sub_team)
    member_config = final_configs.get(member_node.name)
    assert member_config is not None
    assert isinstance(member_config, AgentConfig)

    # Check for member-specific tools
    member_tool_names = {t.get_name() for t in member_config.tools}
    assert UpdateTaskStatus.get_name() in member_tool_names
    assert PublishTaskPlan.get_name() not in member_tool_names # Should not have coordinator tools

    # --- Verify for both ---
    # THE FIX: Check the 'initial_custom_data' attribute on the AgentConfig object.
    assert coord_config.initial_custom_data["team_context"] is agent_team_context
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
