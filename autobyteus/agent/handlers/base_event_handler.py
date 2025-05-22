# file: autobyteus/autobyteus/agent/handlers/base_event_handler.py
import logging
from abc import ABC, abstractmethod
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from autobyteus.agent.context import AgentContext # MODIFIED IMPORT

logger = logging.getLogger(__name__)

class AgentEventHandler(ABC):
    """
    Abstract base class for agent event handlers.
    Event handlers contain the logic for processing specific types of events
    that occur during an agent's lifecycle.
    """

    @abstractmethod
    async def handle(self,
                     event: Any,
                     context: 'AgentContext') -> None:
        """
        Handles a specific event.

        Args:
            event: The event object to handle. This could be any of the defined
                   event types (e.g., UserMessageEvent, ToolInvocationEvent).
            context: The AgentContext, providing access to the agent's state,
                     LLM, tools, and queues.
        
        Raises:
            NotImplementedError: If the subclass does not implement this method.
        """
        raise NotImplementedError("Subclasses must implement the 'handle' method.")

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}>"
