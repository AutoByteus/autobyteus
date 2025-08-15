# file: autobyteus/autobyteus/agent/context/agent_context_registry.py
import logging
from typing import Dict, Optional, TYPE_CHECKING
import weakref

from autobyteus.utils.singleton import SingletonMeta

if TYPE_CHECKING:
    from .agent_context import AgentContext

logger = logging.getLogger(__name__)

class AgentContextRegistry(metaclass=SingletonMeta):
    """
    A singleton registry that holds weak references to active AgentContext objects,
    keyed by their agent_id.

    This allows other services to look up an agent's context without creating
    tight coupling or preventing garbage collection.
    """
    def __init__(self):
        self._contexts: Dict[str, weakref.ReferenceType['AgentContext']] = {}
        logger.info("AgentContextRegistry (Singleton) initialized.")

    def register_context(self, context: 'AgentContext'):
        """
        Registers an agent's context. A weak reference is stored to prevent
        circular references and allow for proper garbage collection.

        Args:
            context: The AgentContext instance to register.
        """
        agent_id = context.agent_id
        if agent_id in self._contexts and self._contexts[agent_id]() is not None:
            logger.warning(f"AgentContext for agent_id '{agent_id}' is already registered. Overwriting.")
        
        self._contexts[agent_id] = weakref.ref(context)
        logger.info(f"Registered AgentContext for agent_id '{agent_id}'. Total registered contexts: {len(self._contexts)}")

    def unregister_context(self, agent_id: str):
        """
        Unregisters an agent's context, typically on agent shutdown.

        Args:
            agent_id: The ID of the agent whose context should be removed.
        """
        if agent_id in self._contexts:
            del self._contexts[agent_id]
            logger.info(f"Unregistered AgentContext for agent_id '{agent_id}'.")
        else:
            logger.warning(f"Attempted to unregister a non-existent AgentContext for agent_id '{agent_id}'.")

    def get_context(self, agent_id: str) -> Optional['AgentContext']:
        """
        Retrieves an active agent's context by its ID.

        Args:
            agent_id: The ID of the agent.

        Returns:
            The AgentContext instance if found and still alive, otherwise None.
        """
        context_ref = self._contexts.get(agent_id)
        if context_ref:
            context = context_ref()
            if context:
                return context
            else:
                # The weak reference is dead, so we can clean it up.
                logger.debug(f"Cleaning up dead weak reference for agent_id '{agent_id}'.")
                del self._contexts[agent_id]
        
        return None
