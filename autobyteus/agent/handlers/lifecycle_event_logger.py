# file: autobyteus/autobyteus/agent/handlers/lifecycle_event_logger.py
import logging
from typing import TYPE_CHECKING

from autobyteus.agent.handlers.base_event_handler import AgentEventHandler
from autobyteus.agent.events import (
    BaseEvent,
    AgentReadyEvent, # MODIFIED: Renamed from AgentStartedEvent
    AgentStoppedEvent,
    AgentErrorEvent,
    LifecycleEvent 
)
from autobyteus.agent.phases import AgentOperationalPhase # Import new phase enum

if TYPE_CHECKING:
    from autobyteus.agent.context import AgentContext 

logger = logging.getLogger(__name__)

class LifecycleEventLogger(AgentEventHandler): 
    """
    Logs various lifecycle events for an agent.
    This handler does not modify agent state directly; phase changes are managed
    by AgentPhaseManager.
    """

    async def handle(self,
                     event: BaseEvent, 
                     context: 'AgentContext') -> None: 
        """
        Logs different lifecycle events.

        Args:
            event: The lifecycle event object (AgentReadyEvent, AgentStoppedEvent, etc.).
            context: The composite AgentContext (used for agent_id and current phase).
        """
        
        agent_id = context.agent_id 
        # MODIFIED: Use current_phase instead of status
        current_phase_val = context.current_phase.value if context.current_phase else "None (Phase not set)"

        if isinstance(event, AgentReadyEvent): # MODIFIED: Check for AgentReadyEvent
            logger.info(f"Agent '{agent_id}' Logged AgentReadyEvent. Current agent phase: {current_phase_val}") # MODIFIED log message

        elif isinstance(event, AgentStoppedEvent):
            logger.info(f"Agent '{agent_id}' Logged AgentStoppedEvent. Current agent phase: {current_phase_val}")

        elif isinstance(event, AgentErrorEvent):
            logger.error(
                f"Agent '{agent_id}' Logged AgentErrorEvent: {event.error_message}. "
                f"Details: {event.exception_details}. Current agent phase: {current_phase_val}"
            )

        else: # pragma: no cover
            if isinstance(event, LifecycleEvent): 
                 logger.warning(
                     f"LifecycleEventLogger for agent '{agent_id}' received an unhandled "
                     f"specific LifecycleEvent type: {type(event)}. Event: {event}. Current phase: {current_phase_val}"
                 )
            else: 
                 logger.warning(
                     f"LifecycleEventLogger for agent '{agent_id}' received an "
                     f"unexpected event type: {type(event)}. Event: {event}. Current phase: {current_phase_val}"
                 )
