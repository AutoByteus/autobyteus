# file: autobyteus/tests/unit_tests/agent_team/bootstrap_steps/test_agent_tool_injection_step.py
import pytest
from unittest.mock import MagicMock

from autobyteus.agent_team.bootstrap_steps.agent_tool_injection_step import AgentToolInjectionStep
from autobyteus.agent_team.context import AgentTeamContext

@pytest.fixture
def tool_injection_step():
    return AgentToolInjectionStep()

@pytest.mark.asyncio
async def test_execute_is_placeholder_and_succeeds(
    tool_injection_step: AgentToolInjectionStep,
    agent_team_context: AgentTeamContext
):
    """
    Tests that the updated AgentToolInjectionStep is a placeholder and simply returns True.
    """
    # --- Execute ---
    success = await tool_injection_step.execute(agent_team_context, agent_team_context.phase_manager)

    # --- Assert ---
    assert success is True
