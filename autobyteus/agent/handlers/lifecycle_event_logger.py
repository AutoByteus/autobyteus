# file: autobyteus/autobyteus/agent/handlers/lifecycle_event_logger.py
import logging
from typing import TYPE_CHECKING

from autobyteus.agent.handlers.base_event_handler import AgentEventHandler
# MODIFIED IMPORTS for events
from autobyteus.agent.events import (
    BaseEvent,
    AgentStartedEvent,
    AgentStoppedEvent,
    AgentErrorEvent,
    LifecycleEvent 
)
from autobyteus.agent.status import AgentStatus # This import seems fine, it's top-level in agent/

if TYPE_CHECKING:
    from autobyteus.agent.context import AgentContext # MODIFIED IMPORT

logger = logging.getLogger(__name__)

class LifecycleEventLogger(AgentEventHandler): 
    """
    Logs various lifecycle events for an agent.
    This handler does not modify agent state directly; status changes are managed
    by AgentStatusManager, which is triggered by AgentRuntime.
    """

    async def handle(self,
                     event: BaseEvent, 
                     context: 'AgentContext') -> None:
        """
        Logs different lifecycle events.

        Args:
            event: The lifecycle event object (AgentStartedEvent, AgentStoppedEvent, etc.).
            context: The AgentContext (used for agent_id in logs and to get current status).
        """
        
        current_status_val = context.status.value if context.status else "None"

        if isinstance(event, AgentStartedEvent):
            logger.info(f"Agent '{context.agent_id}' Logged AgentStartedEvent. Current status context holds: {current_status_val}")
            # Actual status transition to IDLE is handled by AgentStatusManager after this event is processed.

        elif isinstance(event, AgentStoppedEvent):
            logger.info(f"Agent '{context.agent_id}' Logged AgentStoppedEvent. Current status context holds: {current_status_val}")
            # Actual status transition to ENDED is handled by AgentStatusManager around this event.

        elif isinstance(event, AgentErrorEvent):
            logger.error(
                f"Agent '{context.agent_id}' Logged AgentErrorEvent: {event.error_message}. "
                f"Details: {event.exception_details}. Current status context holds: {current_status_val}"
            )
            # Actual status transition to ERROR is handled by AgentStatusManager when error occurs.

        else:
            # Catch any other LifecycleEvent that might be routed here but not explicitly handled above.
            if isinstance(event, LifecycleEvent): 
                 logger.warning(
                     f"LifecycleEventLogger for agent '{context.agent_id}' received an unhandled "
                     f"specific LifecycleEvent type: {type(event)}. Event: {event}. Current status: {current_status_val}"
                 )
            # Catch any non-LifecycleEvent (should not happen if registry is correct).
            else: 
                 logger.warning(
                     f"LifecycleEventLogger for agent '{context.agent_id}' received an "
                     f"unexpected event type: {type(event)}. Event: {event}. Current status: {current_status_val}"
                 )
