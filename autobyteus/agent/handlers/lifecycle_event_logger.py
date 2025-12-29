# file: autobyteus/autobyteus/agent/handlers/lifecycle_event_logger.py
import logging
from typing import TYPE_CHECKING

from autobyteus.agent.handlers.base_event_handler import AgentEventHandler
from autobyteus.agent.events import (
    BaseEvent,
    AgentReadyEvent, # MODIFIED: Renamed from AgentStartedEvent
    AgentStoppedEvent,
    AgentErrorEvent,
    AgentIdleEvent,
    ShutdownRequestedEvent,
    LifecycleEvent 
)
from autobyteus.agent.status.status_enum import AgentStatus # Import new status enum

if TYPE_CHECKING:
    from autobyteus.agent.context import AgentContext 

logger = logging.getLogger(__name__)

class LifecycleEventLogger(AgentEventHandler): 
    """
    Logs various lifecycle events for an agent.
    This handler does not modify agent state directly; status changes are projected
    from events.
    """

    async def handle(self,
                     event: BaseEvent, 
                     context: 'AgentContext') -> None: 
        """
        Logs different lifecycle events.

        Args:
            event: The lifecycle event object (AgentReadyEvent, AgentStoppedEvent, etc.).
            context: The composite AgentContext (used for agent_id and current status).
        """
        
        agent_id = context.agent_id 
        # MODIFIED: Use current_status instead of status
        current_status_val = context.current_status.value if context.current_status else "None (Status not set)"

        if isinstance(event, AgentReadyEvent): # MODIFIED: Check for AgentReadyEvent
            logger.info(f"Agent '{agent_id}' Logged AgentReadyEvent. Current agent status: {current_status_val}") # MODIFIED log message

        elif isinstance(event, AgentStoppedEvent):
            logger.info(f"Agent '{agent_id}' Logged AgentStoppedEvent. Current agent status: {current_status_val}")

        elif isinstance(event, AgentIdleEvent):
            logger.info(f"Agent '{agent_id}' Logged AgentIdleEvent. Current agent status: {current_status_val}")

        elif isinstance(event, ShutdownRequestedEvent):
            logger.info(f"Agent '{agent_id}' Logged ShutdownRequestedEvent. Current agent status: {current_status_val}")

        elif isinstance(event, AgentErrorEvent):
            logger.error(
                f"Agent '{agent_id}' Logged AgentErrorEvent: {event.error_message}. "
                f"Details: {event.exception_details}. Current agent status: {current_status_val}"
            )

        else: # pragma: no cover
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
