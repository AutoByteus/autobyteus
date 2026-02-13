# file: autobyteus/autobyteus/agent/status/status_update_utils.py
import logging
from typing import Optional, Tuple, TYPE_CHECKING

from autobyteus.agent.status.status_enum import AgentStatus
from autobyteus.agent.events.agent_events import (
    AgentErrorEvent,
    PendingToolInvocationEvent,
    ExecuteToolInvocationEvent,
    ToolExecutionApprovalEvent,
    ToolResultEvent,
)

if TYPE_CHECKING:
    from autobyteus.agent.context import AgentContext
    from autobyteus.agent.events.agent_events import BaseEvent

logger = logging.getLogger(__name__)


def build_status_update_data(event: 'BaseEvent',
                             context: 'AgentContext',
                             new_status: AgentStatus) -> Optional[dict]:
    if new_status == AgentStatus.PROCESSING_USER_INPUT:
        return {"trigger": type(event).__name__}

    if new_status == AgentStatus.EXECUTING_TOOL:
        tool_name = None
        if isinstance(event, PendingToolInvocationEvent):
            tool_name = event.tool_invocation.name
        elif isinstance(event, ExecuteToolInvocationEvent):
            tool_name = event.tool_invocation.name
        elif isinstance(event, ToolExecutionApprovalEvent):
            pending_invocation = context.state.pending_tool_approvals.get(event.tool_invocation_id)
            tool_name = pending_invocation.name if pending_invocation else "unknown_tool"
        if tool_name:
            return {"tool_name": tool_name}

    if new_status == AgentStatus.PROCESSING_TOOL_RESULT and isinstance(event, ToolResultEvent):
        return {"tool_name": event.tool_name}

    if new_status == AgentStatus.TOOL_DENIED and isinstance(event, ToolExecutionApprovalEvent):
        pending_invocation = context.state.pending_tool_approvals.get(event.tool_invocation_id)
        tool_name = pending_invocation.name if pending_invocation else "unknown_tool"
        return {"tool_name": tool_name, "denial_for_tool": tool_name}

    if new_status == AgentStatus.ERROR and isinstance(event, AgentErrorEvent):
        return {"error_message": event.error_message, "error_details": event.exception_details}

    return None


async def apply_event_and_derive_status(event: 'BaseEvent',
                                        context: 'AgentContext') -> Tuple[AgentStatus, AgentStatus]:
    if context.state.event_store:
        try:
            context.state.event_store.append(event)
        except Exception as exc:  # pragma: no cover
            logger.error(f"Failed to append event to store: {exc}", exc_info=True)

    if not context.state.status_deriver:
        return context.current_status, context.current_status

    old_status, new_status = context.state.status_deriver.apply(event, context)
    if old_status != new_status:
        context.current_status = new_status
        additional_data = build_status_update_data(event, context, new_status)
        if context.status_manager:
            await context.status_manager.emit_status_update(
                old_status, new_status, additional_data=additional_data
            )

    return old_status, new_status
