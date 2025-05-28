# file: autobyteus/autobyteus/agent/handlers/generic_event_handler.py
import logging
from typing import TYPE_CHECKING, Any

from autobyteus.agent.handlers.base_event_handler import AgentEventHandler
from autobyteus.agent.events import GenericEvent 

if TYPE_CHECKING:
    from autobyteus.agent.context import AgentContext # Composite AgentContext

logger = logging.getLogger(__name__)

class GenericEventHandler(AgentEventHandler):
    """
    Handles GenericEvents.
    This handler can be used as a catch-all or for specific, dynamically-typed
    generic events, using the event's 'type_name' or 'payload' for sub-dispatch.
    """
    def __init__(self):
        logger.info("GenericEventHandler initialized.")

    async def handle(self,
                     event: GenericEvent, 
                     context: 'AgentContext') -> None: # context is composite
        """
        Handles a GenericEvent.

        Args:
            event: The GenericEvent object to handle.
            context: The composite AgentContext.
        """
        if not isinstance(event, GenericEvent): 
            logger.warning(f"GenericEventHandler received a non-GenericEvent: {type(event)}. Skipping.")
            return
        
        agent_id = context.agent_id # Using convenience property

        logger.info(f"Agent '{agent_id}' handling GenericEvent with type_name: '{event.type_name}'. Payload: {event.payload}")

        if event.type_name == "example_custom_generic_event":
            logger.info(f"Handling specific generic event 'example_custom_generic_event' for agent '{agent_id}'.")
        elif event.type_name == "another_custom_event":
            logger.info(f"Handling specific generic event 'another_custom_event' for agent '{agent_id}'.")
        else:
            logger.warning(f"Agent '{agent_id}' received GenericEvent with unhandled type_name: '{event.type_name}'.")

