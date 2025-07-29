# file: autobyteus/tests/unit_tests/workflow/bootstrap_steps/test_agent_tool_injection_step.py
import pytest
from unittest.mock import MagicMock, ANY

from autobyteus.workflow.bootstrap_steps.agent_tool_injection_step import AgentToolInjectionStep
from autobyteus.workflow.context import WorkflowContext, TeamManager
from autobyteus.agent.message.send_message_to import SendMessageTo

@pytest.fixture
def tool_injection_step():
    return AgentToolInjectionStep()

@pytest.mark.asyncio
async def test_execute_success(
    tool_injection_step: AgentToolInjectionStep,
    workflow_context: WorkflowContext,
    mock_workflow_phase_manager: MagicMock
):
    """
    Tests successful execution of the tool injection step.
    """
    # --- Setup ---
    # Simulate state from the previous step
    prepared_prompt = "This is the prepared prompt for the coordinator."
    workflow_context.state.prepared_coordinator_prompt = prepared_prompt
    mock_team_manager = workflow_context.team_manager
    
    # --- Execute ---
    success = await tool_injection_step.execute(workflow_context, mock_workflow_phase_manager)

    # --- Assert ---
    assert success is True
    
    # Verify that the team manager was populated with the final configs
    mock_team_manager.set_agent_configs.assert_called_once()
    
    # Inspect the configs that were passed to the team manager
    final_configs_map = mock_team_manager.set_agent_configs.call_args[0][0]
    assert isinstance(final_configs_map, dict)
    assert len(final_configs_map) == 2
    assert "Coordinator" in final_configs_map
    assert "Member" in final_configs_map
    
    # 1. Check the Coordinator's final config
    coordinator_config = final_configs_map["Coordinator"]
    assert coordinator_config.system_prompt == prepared_prompt
    assert any(isinstance(tool, SendMessageTo) for tool in coordinator_config.tools)
    # Check that the injected tool has the team manager instance
    injected_tool_coord = next(t for t in coordinator_config.tools if isinstance(t, SendMessageTo))
    assert injected_tool_coord._team_manager is mock_team_manager
    
    # 2. Check the Member's final config
    member_config = final_configs_map["Member"]
    original_member_node = next(n for n in workflow_context.config.nodes if n.name == "Member")
    # The member's prompt should be unchanged by this step.
    assert member_config.system_prompt == original_member_node.effective_config.system_prompt

@pytest.mark.asyncio
@pytest.mark.parametrize("missing_data", ["team_manager", "prompt"])
async def test_execute_failure_on_missing_state(
    tool_injection_step: AgentToolInjectionStep,
    workflow_context: WorkflowContext,
    mock_workflow_phase_manager: MagicMock,
    missing_data: str
):
    """
    Tests that the step fails gracefully if required state from previous steps is missing.
    """
    # Keep a reference to the original mock, as we might set the context's reference to None
    mock_team_manager = workflow_context.team_manager

    if missing_data == "team_manager":
        workflow_context.state.team_manager = None
        workflow_context.state.prepared_coordinator_prompt = "prompt exists"
    else: # "prompt"
        workflow_context.state.prepared_coordinator_prompt = None

    success = await tool_injection_step.execute(workflow_context, mock_workflow_phase_manager)

    assert success is False
    
    # Only check for method calls if the team manager was expected to exist.
    if missing_data == "prompt":
        mock_team_manager.set_agent_configs.assert_not_called()
