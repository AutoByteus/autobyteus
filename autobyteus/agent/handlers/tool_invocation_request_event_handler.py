import logging
from typing import TYPE_CHECKING, Optional

from autobyteus.agent.handlers.base_event_handler import AgentEventHandler
from autobyteus.agent.events import PendingToolInvocationEvent, ExecuteToolInvocationEvent
from autobyteus.agent.handlers.tool_lifecycle_payload import (
    build_tool_lifecycle_payload_from_invocation,
)

if TYPE_CHECKING:
    from autobyteus.agent.context import AgentContext
    from autobyteus.agent.events.notifiers import AgentExternalEventNotifier

logger = logging.getLogger(__name__)


class ToolInvocationRequestEventHandler(AgentEventHandler):
    """Handles PendingToolInvocationEvent by requesting approval or scheduling execution."""

    def __init__(self):  # pragma: no cover
        logger.info("ToolInvocationRequestEventHandler initialized.")

    async def handle(self, event: PendingToolInvocationEvent, context: "AgentContext") -> None:  # pragma: no cover
        if not isinstance(event, PendingToolInvocationEvent):
            logger.warning(
                "ToolInvocationRequestEventHandler received non-PendingToolInvocationEvent: %s. Skipping.",
                type(event),
            )
            return

        tool_invocation = event.tool_invocation
        agent_id = context.agent_id

        notifier: Optional["AgentExternalEventNotifier"] = None
        if context.status_manager:
            notifier = context.status_manager.notifier

        if not context.auto_execute_tools:
            if not notifier:
                logger.error(
                    "Agent '%s': Notifier is required for manual approval flow but unavailable.",
                    agent_id,
                )
                return

            context.store_pending_tool_invocation(tool_invocation)
            try:
                notifier.notify_agent_tool_approval_requested(
                    {
                        **build_tool_lifecycle_payload_from_invocation(agent_id, tool_invocation),
                        "arguments": tool_invocation.arguments,
                    }
                )
            except Exception as notify_error:  # pragma: no cover
                logger.error(
                    "Agent '%s': Error notifying tool approval requested event: %s",
                    agent_id,
                    notify_error,
                    exc_info=True,
                )
            return

        await context.input_event_queues.enqueue_internal_system_event(
            ExecuteToolInvocationEvent(tool_invocation=tool_invocation)
        )
