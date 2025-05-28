# file: autobyteus/autobyteus/agent/handlers/base_event_handler.py
import logging
from abc import ABC, abstractmethod
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    # Ensure this points to the new composite AgentContext
    from autobyteus.agent.context.agent_context import AgentContext 

logger = logging.getLogger(__name__)

class AgentEventHandler(ABC):
    """
    Abstract base class for agent event handlers.
    Event handlers contain the logic for processing specific types of events
    that occur during an agent's lifecycle.
    """

    @abstractmethod
    async def handle(self,
                     event: Any, # Specific event type will be in subclass
                     context: 'AgentContext') -> None: # context is now the composite AgentContext
        """
        Handles a specific event.

        Args:
            event: The event object to handle.
            context: The composite AgentContext, providing access to agent's config and state.
        
        Raises:
            NotImplementedError: If the subclass does not implement this method.
        """
        raise NotImplementedError("Subclasses must implement the 'handle' method.")

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}>"
