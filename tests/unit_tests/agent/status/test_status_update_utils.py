# file: autobyteus/tests/unit_tests/agent/status/test_status_update_utils.py
import pytest
from unittest.mock import MagicMock, AsyncMock

from autobyteus.agent.status.status_enum import AgentStatus
from autobyteus.agent.status.status_update_utils import build_status_update_data, apply_event_and_derive_status
from autobyteus.agent.status.status_deriver import AgentStatusDeriver
from autobyteus.agent.events.agent_events import (
    UserMessageReceivedEvent,
    PendingToolInvocationEvent,
    ToolExecutionApprovalEvent,
    ApprovedToolInvocationEvent,
    ToolResultEvent,
    AgentErrorEvent,
)
from autobyteus.agent.tool_invocation import ToolInvocation
from autobyteus.agent.events.event_store import AgentEventStore


def test_build_status_update_data_processing_user_input(agent_context):
    event = UserMessageReceivedEvent(agent_input_user_message=MagicMock())
    data = build_status_update_data(event, agent_context, AgentStatus.PROCESSING_USER_INPUT)
    assert data == {"trigger": "UserMessageReceivedEvent"}


def test_build_status_update_data_executing_tool_pending_invocation(agent_context):
    invocation = ToolInvocation(name="test_tool", arguments={}, id="tid1")
    event = PendingToolInvocationEvent(tool_invocation=invocation)
    data = build_status_update_data(event, agent_context, AgentStatus.EXECUTING_TOOL)
    assert data == {"tool_name": "test_tool"}


def test_build_status_update_data_executing_tool_approved_invocation(agent_context):
    invocation = ToolInvocation(name="approved_tool", arguments={}, id="tid2")
    event = ApprovedToolInvocationEvent(tool_invocation=invocation)
    data = build_status_update_data(event, agent_context, AgentStatus.EXECUTING_TOOL)
    assert data == {"tool_name": "approved_tool"}


def test_build_status_update_data_execution_approval_unknown_tool(agent_context):
    event = ToolExecutionApprovalEvent(tool_invocation_id="missing", is_approved=True)
    agent_context.state.pending_tool_approvals = {}
    data = build_status_update_data(event, agent_context, AgentStatus.EXECUTING_TOOL)
    assert data == {"tool_name": "unknown_tool"}


def test_build_status_update_data_tool_denied(agent_context):
    invocation = ToolInvocation(name="deny_tool", arguments={}, id="tid3")
    agent_context.state.pending_tool_approvals = {"tid3": invocation}
    event = ToolExecutionApprovalEvent(tool_invocation_id="tid3", is_approved=False)
    data = build_status_update_data(event, agent_context, AgentStatus.TOOL_DENIED)
    assert data == {"tool_name": "deny_tool", "denial_for_tool": "deny_tool"}


def test_build_status_update_data_processing_tool_result(agent_context):
    event = ToolResultEvent(tool_name="tool_result", result="ok")
    data = build_status_update_data(event, agent_context, AgentStatus.PROCESSING_TOOL_RESULT)
    assert data == {"tool_name": "tool_result"}


def test_build_status_update_data_error(agent_context):
    event = AgentErrorEvent(error_message="boom", exception_details="trace")
    data = build_status_update_data(event, agent_context, AgentStatus.ERROR)
    assert data == {"error_message": "boom", "error_details": "trace"}


@pytest.mark.asyncio
async def test_apply_event_and_derive_status_updates_status_and_emits(agent_context):
    agent_context.state.status_deriver = AgentStatusDeriver(initial_status=AgentStatus.IDLE)
    agent_context.current_status = AgentStatus.IDLE
    agent_context.state.event_store = AgentEventStore(agent_id=agent_context.agent_id)
    agent_context.status_manager.emit_status_update = AsyncMock()

    event = UserMessageReceivedEvent(agent_input_user_message=MagicMock())

    old_status, new_status = await apply_event_and_derive_status(event, agent_context)

    assert old_status == AgentStatus.IDLE
    assert new_status == AgentStatus.PROCESSING_USER_INPUT
    assert agent_context.current_status == AgentStatus.PROCESSING_USER_INPUT
    agent_context.status_manager.emit_status_update.assert_awaited_once()
    call_args, call_kwargs = agent_context.status_manager.emit_status_update.call_args
    assert call_args == (AgentStatus.IDLE, AgentStatus.PROCESSING_USER_INPUT)
    assert call_kwargs["additional_data"] == {"trigger": "UserMessageReceivedEvent"}
    assert len(agent_context.state.event_store.all_events()) == 1


@pytest.mark.asyncio
async def test_apply_event_and_derive_status_no_deriver(agent_context):
    agent_context.state.status_deriver = None
    agent_context.current_status = AgentStatus.IDLE
    agent_context.status_manager.emit_status_update = AsyncMock()

    event = UserMessageReceivedEvent(agent_input_user_message=MagicMock())

    old_status, new_status = await apply_event_and_derive_status(event, agent_context)

    assert old_status == AgentStatus.IDLE
    assert new_status == AgentStatus.IDLE
    agent_context.status_manager.emit_status_update.assert_not_awaited()
