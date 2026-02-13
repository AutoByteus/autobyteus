import logging
from typing import TYPE_CHECKING

from autobyteus.agent.handlers.base_event_handler import AgentEventHandler
from autobyteus.agent.events import (
    ToolExecutionApprovalEvent,
    ExecuteToolInvocationEvent,
    ToolResultEvent,
)
from autobyteus.agent.handlers.tool_lifecycle_payload import (
    build_tool_lifecycle_payload_from_invocation,
)

if TYPE_CHECKING:
    from autobyteus.agent.context import AgentContext

logger = logging.getLogger(__name__)


class ToolExecutionApprovalEventHandler(AgentEventHandler):
    """Handles ToolExecutionApprovalEvent by approving or denying pending invocations."""

    def __init__(self):
        logger.info("ToolExecutionApprovalEventHandler initialized.")

    async def handle(self, event: ToolExecutionApprovalEvent, context: "AgentContext") -> None:
        if not isinstance(event, ToolExecutionApprovalEvent):
            logger.warning(
                "ToolExecutionApprovalEventHandler received non-ToolExecutionApprovalEvent: %s. Skipping.",
                type(event),
            )
            return

        retrieved_invocation = context.state.retrieve_pending_tool_invocation(event.tool_invocation_id)
        if not retrieved_invocation:
            logger.warning(
                "Agent '%s': No pending tool invocation found for ID '%s'. Ignoring stale approval.",
                context.agent_id,
                event.tool_invocation_id,
            )
            return

        notifier = context.status_manager.notifier if context.status_manager else None

        if event.is_approved:
            if notifier:
                try:
                    notifier.notify_agent_tool_approved(
                        {
                            **build_tool_lifecycle_payload_from_invocation(
                                context.agent_id,
                                retrieved_invocation,
                            ),
                            "reason": event.reason,
                        }
                    )
                except Exception as notify_error:  # pragma: no cover
                    logger.error(
                        "Agent '%s': Error notifying tool approved event: %s",
                        context.agent_id,
                        notify_error,
                        exc_info=True,
                    )

            await context.input_event_queues.enqueue_internal_system_event(
                ExecuteToolInvocationEvent(tool_invocation=retrieved_invocation)
            )
            return

        denial_reason = event.reason or "Tool execution was denied by user/system."

        if notifier:
            try:
                notifier.notify_agent_tool_denied(
                    {
                        **build_tool_lifecycle_payload_from_invocation(
                            context.agent_id,
                            retrieved_invocation,
                        ),
                        "reason": denial_reason,
                        "error": denial_reason,
                    }
                )
            except Exception as notify_error:  # pragma: no cover
                logger.error(
                    "Agent '%s': Error notifying tool denied event: %s",
                    context.agent_id,
                    notify_error,
                    exc_info=True,
                )

        await context.input_event_queues.enqueue_tool_result(
            ToolResultEvent(
                tool_name=retrieved_invocation.name,
                result=None,
                tool_invocation_id=retrieved_invocation.id,
                error=denial_reason,
                tool_args=retrieved_invocation.arguments,
                turn_id=retrieved_invocation.turn_id or context.state.active_turn_id,
                is_denied=True,
            )
        )
