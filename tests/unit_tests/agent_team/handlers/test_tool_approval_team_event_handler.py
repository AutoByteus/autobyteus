# file: autobyteus/tests/unit_tests/agent_team/handlers/test_tool_approval_team_event_handler.py
import pytest
from unittest.mock import AsyncMock

from autobyteus.agent_team.handlers.tool_approval_team_event_handler import ToolApprovalTeamEventHandler
from autobyteus.agent_team.events.agent_team_events import ToolApprovalTeamEvent, AgentTeamErrorEvent
from autobyteus.agent_team.context import AgentTeamContext
from autobyteus.agent.agent import Agent

@pytest.fixture
def handler():
    return ToolApprovalTeamEventHandler()

@pytest.fixture
def event():
    return ToolApprovalTeamEvent(
        agent_name="ApproverAgent",
        tool_invocation_id="tool-call-123",
        is_approved=True,
        reason="User approved"
    )

@pytest.mark.asyncio
async def test_handle_success(handler: ToolApprovalTeamEventHandler, event: ToolApprovalTeamEvent, agent_team_context: AgentTeamContext, mock_agent: Agent):
    """
    Tests the happy path where the handler gets the target agent and posts the approval.
    """
    agent_team_context.team_manager.ensure_node_is_ready = AsyncMock(return_value=mock_agent)

    await handler.handle(event, agent_team_context)

    agent_team_context.team_manager.ensure_node_is_ready.assert_awaited_once_with(name_or_agent_id=event.agent_name)
    
    mock_agent.post_tool_execution_approval.assert_awaited_once_with(
        tool_invocation_id=event.tool_invocation_id,
        is_approved=event.is_approved,
        reason=event.reason
    )

@pytest.mark.asyncio
async def test_handle_agent_not_found(handler: ToolApprovalTeamEventHandler, event: ToolApprovalTeamEvent, agent_team_context: AgentTeamContext):
    """
    Tests failure when the target agent for approval is not found.
    """
    agent_team_context.team_manager.ensure_node_is_ready = AsyncMock(return_value=None)

    await handler.handle(event, agent_team_context)

    agent_team_context.state.input_event_queues.enqueue_internal_system_event.assert_awaited_once()
    enqueued_event = agent_team_context.state.input_event_queues.enqueue_internal_system_event.call_args.args[0]
    assert isinstance(enqueued_event, AgentTeamErrorEvent)
