# file: autobyteus/autobyteus/agent/handlers/event_handler_registry.py
import logging
from typing import Dict, Type, Optional

from autobyteus.agent.events import BaseEvent # MODIFIED IMPORT
from autobyteus.agent.handlers.base_event_handler import AgentEventHandler

logger = logging.getLogger(__name__)

class EventHandlerRegistry:
    """
    Manages the registration and retrieval of event handlers based on event types.
    Maps event classes (types) to their corresponding handler instances.
    """

    def __init__(self):
        """Initializes the EventHandlerRegistry with an empty handler mapping."""
        self._handlers: Dict[Type[BaseEvent], AgentEventHandler] = {}
        logger.info("EventHandlerRegistry initialized.")

    def register(self, event_class: Type[BaseEvent], handler_instance: AgentEventHandler) -> None:
        """
        Registers an event handler for a specific event class.

        Args:
            event_class: The class of the event (e.g., UserMessageReceivedEvent).
            handler_instance: An instance of the handler for this event type.

        Raises:
            TypeError: If event_class is not a subclass of BaseEvent or handler_instance is not AgentEventHandler.
            ValueError: If a handler is already registered for the event_class.
        """
        if not isinstance(event_class, type) or not issubclass(event_class, BaseEvent):
            msg = f"Cannot register handler: 'event_class' must be a subclass of BaseEvent, got {event_class}."
            logger.error(msg)
            raise TypeError(msg)
        
        if not isinstance(handler_instance, AgentEventHandler): # Check for handler type
            msg = f"Cannot register handler: 'handler_instance' must be an instance of AgentEventHandler, got {type(handler_instance).__name__}."
            logger.error(msg)
            raise TypeError(msg)

        if event_class in self._handlers:
            msg = f"Handler already registered for event class '{event_class.__name__}'. Overwriting is not allowed by default."
            logger.error(msg)
            raise ValueError(msg)
        
        self._handlers[event_class] = handler_instance
        logger.info(f"Handler '{type(handler_instance).__name__}' registered for event class '{event_class.__name__}'.")

    def get_handler(self, event_class: Type[BaseEvent]) -> Optional[AgentEventHandler]:
        """
        Retrieves the registered event handler for a given event class.

        Args:
            event_class: The class of the event for which to find a handler.

        Returns:
            The registered AgentEventHandler instance if found, otherwise None.
        """
        if not isinstance(event_class, type) or not issubclass(event_class, BaseEvent):
            logger.warning(f"Attempted to get handler for invalid event_class type: {event_class}.")
            return None
            
        handler = self._handlers.get(event_class)
        if not handler:
            logger.debug(f"No handler found for event class '{event_class.__name__}'.")
        return handler

    def get_all_registered_event_types(self) -> list[Type[BaseEvent]]:
        """Returns a list of all event types that have registered handlers."""
        return list(self._handlers.keys())

    def __repr__(self) -> str:
        registered_types = [cls.__name__ for cls in self._handlers.keys()]
        return f"<EventHandlerRegistry registered_event_types={registered_types}>"
