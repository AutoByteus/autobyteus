# file: autobyteus/tests/unit_tests/workflow/bootstrap_steps/test_coordinator_and_team_context_initialization_step.py
import pytest
import logging
from unittest.mock import MagicMock

from autobyteus.agent.workflow.bootstrap_steps.coordinator_and_team_context_initialization_step import CoordinatorAndTeamContextInitializationStep
from autobyteus.agent.workflow.context import WorkflowContext
from autobyteus.agent.agent import Agent
from autobyteus.agent.message.send_message_to import SendMessageTo

@pytest.fixture
def init_step():
    """Provides a clean instance of CoordinatorAndTeamContextInitializationStep."""
    return CoordinatorAndTeamContextInitializationStep()

@pytest.mark.asyncio
async def test_execute_success(
    init_step: CoordinatorAndTeamContextInitializationStep,
    workflow_context: WorkflowContext,
    mock_workflow_phase_manager: MagicMock,
    mock_agent: Agent,
    monkeypatch
):
    """
    Tests the successful execution of the step, verifying coordinator creation,
    TeamContext instantiation, and dependency injection.
    """
    # --- Setup ---
    # 1. Simulate the state left by the previous step (CoordinatorPromptPreparationStep)
    member_node = next(n for n in workflow_context.config.nodes if n != workflow_context.config.coordinator_node)
    workflow_context.state.modified_coordinator_config = workflow_context.config.coordinator_node.agent_config
    workflow_context.state.member_node_ids = {member_node: "Member"}

    # 2. Mock external dependencies that are instantiated within the step
    mock_agent_factory_instance = MagicMock()
    mock_agent_factory_instance.create_agent.return_value = mock_agent
    mock_agent_factory_class = MagicMock(return_value=mock_agent_factory_instance)
    monkeypatch.setattr(
        "autobyteus.agent.workflow.bootstrap_steps.coordinator_and_team_context_initialization_step.AgentFactory",
        mock_agent_factory_class
    )
    
    mock_team_context_instance = MagicMock()
    mock_team_context_class = MagicMock(return_value=mock_team_context_instance)
    monkeypatch.setattr(
        "autobyteus.agent.workflow.bootstrap_steps.coordinator_and_team_context_initialization_step.TeamContext",
        mock_team_context_class
    )
    
    # --- Execute ---
    success = await init_step.execute(workflow_context, mock_workflow_phase_manager)

    # --- Assert ---
    assert success is True
    
    # Verify coordinator agent was created and stored
    mock_agent_factory_instance.create_agent.assert_called_once_with(config=workflow_context.state.modified_coordinator_config)
    assert workflow_context.state.coordinator_agent is mock_agent
    assert workflow_context.state.agents == [mock_agent]

    # Verify TeamContext was instantiated correctly
    expected_node_map = { "Member": member_node }
    mock_team_context_class.assert_called_once_with(
        workflow_id=workflow_context.workflow_id,
        node_configs_by_friendly_name=expected_node_map,
        context=workflow_context
    )
    
    # Verify dependencies were injected into the coordinator
    assert mock_agent.context.custom_data['team_context'] is mock_team_context_instance
    assert 'submit_workflow_event' in mock_agent.context.custom_data
    
    # Verify SendMessageTo tool was injected
    assert any(isinstance(t, SendMessageTo) for t in mock_agent.context.config.tools)

@pytest.mark.asyncio
async def test_execute_failure_on_agent_creation(
    init_step: CoordinatorAndTeamContextInitializationStep,
    workflow_context: WorkflowContext,
    mock_workflow_phase_manager: MagicMock,
    monkeypatch,
    caplog
):
    """
    Tests the failure path where the AgentFactory fails to create the coordinator.
    """
    # Setup: Simulate previous step's state
    workflow_context.state.modified_coordinator_config = workflow_context.config.coordinator_node.agent_config
    workflow_context.state.member_node_ids = {} # Not needed for this test

    # Setup: Mock AgentFactory to raise an error
    error_message = "LLM instance is invalid"
    mock_agent_factory_class = MagicMock()
    mock_agent_factory_class.return_value.create_agent.side_effect = ValueError(error_message)
    monkeypatch.setattr(
        "autobyteus.agent.workflow.bootstrap_steps.coordinator_and_team_context_initialization_step.AgentFactory",
        mock_agent_factory_class
    )

    with caplog.at_level(logging.ERROR):
        success = await init_step.execute(workflow_context, mock_workflow_phase_manager)
    
    assert success is False
    assert f"Failed to initialize agent team: {error_message}" in caplog.text

    # Verify state was not modified
    assert workflow_context.state.coordinator_agent is None
    assert not workflow_context.state.agents

def test_inject_send_message_tool(init_step):
    """
    Tests the private helper method `_inject_send_message_tool` directly.
    """
    # Case 1: Tool is not present, should be added
    initial_tools = [MagicMock()]
    updated_tools = init_step._inject_send_message_tool(initial_tools)
    assert len(updated_tools) == 2
    assert any(isinstance(t, SendMessageTo) for t in updated_tools)
    
    # Case 2: Tool is already present, list should not change
    initial_tools_with_tool = [MagicMock(), SendMessageTo()]
    updated_tools_with_tool = init_step._inject_send_message_tool(initial_tools_with_tool)
    assert len(updated_tools_with_tool) == 2
    # Verify it's the same instance, not a new one
    assert updated_tools_with_tool is initial_tools_with_tool
