# file: autobyteus/autobyteus/agent/handlers/lifecycle_event_logger.py
import logging
from typing import TYPE_CHECKING

from autobyteus.agent.handlers.base_event_handler import AgentEventHandler
from autobyteus.agent.events import (
    BaseEvent,
    AgentStartedEvent,
    AgentStoppedEvent,
    AgentErrorEvent,
    LifecycleEvent 
)
# AgentStatus import is fine as is.

if TYPE_CHECKING:
    from autobyteus.agent.context import AgentContext # Composite AgentContext

logger = logging.getLogger(__name__)

class LifecycleEventLogger(AgentEventHandler): 
    """
    Logs various lifecycle events for an agent.
    This handler does not modify agent state directly; status changes are managed
    by AgentStatusManager, which is triggered by AgentRuntime.
    """

    async def handle(self,
                     event: BaseEvent, 
                     context: 'AgentContext') -> None: # context is composite
        """
        Logs different lifecycle events.

        Args:
            event: The lifecycle event object (AgentStartedEvent, AgentStoppedEvent, etc.).
            context: The composite AgentContext (used for agent_id and current status).
        """
        
        agent_id = context.agent_id # Using convenience property
        current_status_val = context.status.value if context.status else "None" # Using convenience property

        if isinstance(event, AgentStartedEvent):
            logger.info(f"Agent '{agent_id}' Logged AgentStartedEvent. Current status context holds: {current_status_val}")

        elif isinstance(event, AgentStoppedEvent):
            logger.info(f"Agent '{agent_id}' Logged AgentStoppedEvent. Current status context holds: {current_status_val}")

        elif isinstance(event, AgentErrorEvent):
            logger.error(
                f"Agent '{agent_id}' Logged AgentErrorEvent: {event.error_message}. "
                f"Details: {event.exception_details}. Current status context holds: {current_status_val}"
            )

        else:
            if isinstance(event, LifecycleEvent): 
                 logger.warning(
                     f"LifecycleEventLogger for agent '{agent_id}' received an unhandled "
                     f"specific LifecycleEvent type: {type(event)}. Event: {event}. Current status: {current_status_val}"
                 )
            else: 
                 logger.warning(
                     f"LifecycleEventLogger for agent '{agent_id}' received an "
                     f"unexpected event type: {type(event)}. Event: {event}. Current status: {current_status_val}"
                 )

