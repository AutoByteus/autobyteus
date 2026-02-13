# file: autobyteus/tests/unit_tests/agent/status/test_status_deriver.py
import pytest
from unittest.mock import MagicMock

from autobyteus.agent.status.status_deriver import AgentStatusDeriver
from autobyteus.agent.status.status_enum import AgentStatus
from autobyteus.agent.events.agent_events import (
    BootstrapStartedEvent,
    BootstrapCompletedEvent,
    AgentReadyEvent,
    AgentIdleEvent,
    ShutdownRequestedEvent,
    AgentStoppedEvent,
    AgentErrorEvent,
    UserMessageReceivedEvent,
    InterAgentMessageReceivedEvent,
    LLMUserMessageReadyEvent,
    LLMCompleteResponseReceivedEvent,
    PendingToolInvocationEvent,
    ToolExecutionApprovalEvent,
    ExecuteToolInvocationEvent,
    ToolResultEvent,
)
from autobyteus.agent.tool_invocation import ToolInvocation


def test_bootstrap_and_ready_transitions():
    deriver = AgentStatusDeriver(initial_status=AgentStatus.UNINITIALIZED)
    old_status, new_status = deriver.apply(BootstrapStartedEvent())
    assert old_status == AgentStatus.UNINITIALIZED
    assert new_status == AgentStatus.BOOTSTRAPPING
    assert deriver.current_status == AgentStatus.BOOTSTRAPPING

    old_status, new_status = deriver.apply(BootstrapCompletedEvent(success=True))
    assert old_status == AgentStatus.BOOTSTRAPPING
    assert new_status == AgentStatus.BOOTSTRAPPING

    old_status, new_status = deriver.apply(AgentReadyEvent())
    assert old_status == AgentStatus.BOOTSTRAPPING
    assert new_status == AgentStatus.IDLE

    old_status, new_status = deriver.apply(AgentIdleEvent())
    assert old_status == AgentStatus.IDLE
    assert new_status == AgentStatus.IDLE


def test_shutdown_and_error_transitions():
    deriver = AgentStatusDeriver(initial_status=AgentStatus.IDLE)
    old_status, new_status = deriver.apply(ShutdownRequestedEvent())
    assert old_status == AgentStatus.IDLE
    assert new_status == AgentStatus.SHUTTING_DOWN

    deriver = AgentStatusDeriver(initial_status=AgentStatus.ERROR)
    old_status, new_status = deriver.apply(ShutdownRequestedEvent())
    assert old_status == AgentStatus.ERROR
    assert new_status == AgentStatus.ERROR

    deriver = AgentStatusDeriver(initial_status=AgentStatus.IDLE)
    old_status, new_status = deriver.apply(AgentStoppedEvent())
    assert new_status == AgentStatus.SHUTDOWN_COMPLETE

    deriver = AgentStatusDeriver(initial_status=AgentStatus.ERROR)
    old_status, new_status = deriver.apply(AgentStoppedEvent())
    assert new_status == AgentStatus.ERROR

    old_status, new_status = deriver.apply(AgentErrorEvent(error_message="boom", exception_details="trace"))
    assert new_status == AgentStatus.ERROR


def test_user_message_and_llm_transitions():
    deriver = AgentStatusDeriver(initial_status=AgentStatus.IDLE)
    event = UserMessageReceivedEvent(agent_input_user_message=MagicMock())
    old_status, new_status = deriver.apply(event)
    assert new_status == AgentStatus.PROCESSING_USER_INPUT

    deriver = AgentStatusDeriver(initial_status=AgentStatus.IDLE)
    event = InterAgentMessageReceivedEvent(inter_agent_message=MagicMock())
    old_status, new_status = deriver.apply(event)
    assert new_status == AgentStatus.PROCESSING_USER_INPUT

    deriver = AgentStatusDeriver(initial_status=AgentStatus.PROCESSING_USER_INPUT)
    event = LLMUserMessageReadyEvent(llm_user_message=MagicMock())
    old_status, new_status = deriver.apply(event)
    assert new_status == AgentStatus.AWAITING_LLM_RESPONSE

    deriver = AgentStatusDeriver(initial_status=AgentStatus.AWAITING_LLM_RESPONSE)
    event = LLMUserMessageReadyEvent(llm_user_message=MagicMock())
    old_status, new_status = deriver.apply(event)
    assert new_status == AgentStatus.AWAITING_LLM_RESPONSE

    deriver = AgentStatusDeriver(initial_status=AgentStatus.ERROR)
    old_status, new_status = deriver.apply(LLMUserMessageReadyEvent(llm_user_message=MagicMock()))
    assert new_status == AgentStatus.ERROR

    deriver = AgentStatusDeriver(initial_status=AgentStatus.AWAITING_LLM_RESPONSE)
    event = LLMCompleteResponseReceivedEvent(complete_response=MagicMock())
    old_status, new_status = deriver.apply(event)
    assert new_status == AgentStatus.ANALYZING_LLM_RESPONSE

    deriver = AgentStatusDeriver(initial_status=AgentStatus.IDLE)
    event = LLMCompleteResponseReceivedEvent(complete_response=MagicMock())
    old_status, new_status = deriver.apply(event)
    assert new_status == AgentStatus.IDLE


def test_tool_related_transitions():
    tool_invocation = ToolInvocation(name="tool", arguments={}, id="tid1")
    pending_event = PendingToolInvocationEvent(tool_invocation=tool_invocation)

    context = MagicMock()
    context.auto_execute_tools = False
    deriver = AgentStatusDeriver(initial_status=AgentStatus.IDLE)
    old_status, new_status = deriver.apply(pending_event, context)
    assert new_status == AgentStatus.AWAITING_TOOL_APPROVAL

    context.auto_execute_tools = True
    deriver = AgentStatusDeriver(initial_status=AgentStatus.IDLE)
    old_status, new_status = deriver.apply(pending_event, context)
    assert new_status == AgentStatus.EXECUTING_TOOL

    approved_event = ExecuteToolInvocationEvent(tool_invocation=tool_invocation)
    deriver = AgentStatusDeriver(initial_status=AgentStatus.IDLE)
    old_status, new_status = deriver.apply(approved_event, context)
    assert new_status == AgentStatus.EXECUTING_TOOL

    approval_event = ToolExecutionApprovalEvent(tool_invocation_id="tid1", is_approved=True)
    deriver = AgentStatusDeriver(initial_status=AgentStatus.IDLE)
    old_status, new_status = deriver.apply(approval_event, context)
    assert new_status == AgentStatus.EXECUTING_TOOL

    approval_event = ToolExecutionApprovalEvent(tool_invocation_id="tid1", is_approved=False)
    deriver = AgentStatusDeriver(initial_status=AgentStatus.IDLE)
    old_status, new_status = deriver.apply(approval_event, context)
    assert new_status == AgentStatus.TOOL_DENIED

    result_event = ToolResultEvent(tool_name="tool", result="ok")
    deriver = AgentStatusDeriver(initial_status=AgentStatus.IDLE)
    old_status, new_status = deriver.apply(result_event, context)
    assert new_status == AgentStatus.IDLE

    deriver = AgentStatusDeriver(initial_status=AgentStatus.EXECUTING_TOOL)
    old_status, new_status = deriver.apply(result_event, context)
    assert new_status == AgentStatus.PROCESSING_TOOL_RESULT
