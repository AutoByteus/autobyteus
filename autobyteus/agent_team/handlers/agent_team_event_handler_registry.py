# file: autobyteus/autobyteus/agent_team/handlers/agent_team_event_handler_registry.py
import logging
from typing import Dict, Type, Optional

from autobyteus.agent_team.handlers.base_agent_team_event_handler import BaseAgentTeamEventHandler
from autobyteus.agent_team.events.agent_team_events import BaseAgentTeamEvent

logger = logging.getLogger(__name__)

class AgentTeamEventHandlerRegistry:
    """Manages registration and retrieval of agent team event handlers."""
    def __init__(self):
        self._handlers: Dict[Type[BaseAgentTeamEvent], BaseAgentTeamEventHandler] = {}
        logger.info("AgentTeamEventHandlerRegistry initialized.")

    def register(self, event_class: Type[BaseAgentTeamEvent], handler_instance: BaseAgentTeamEventHandler):
        if not issubclass(event_class, BaseAgentTeamEvent):
            raise TypeError("Can only register handlers for BaseAgentTeamEvent subclasses.")
        self._handlers[event_class] = handler_instance
        logger.info(f"Handler '{type(handler_instance).__name__}' registered for event '{event_class.__name__}'.")

    def get_handler(self, event_class: Type[BaseAgentTeamEvent]) -> Optional[BaseAgentTeamEventHandler]:
        return self._handlers.get(event_class)
