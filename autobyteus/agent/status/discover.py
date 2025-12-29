# file: autobyteus/autobyteus/agent/status/discover.py
import inspect
import logging
from typing import List, Optional, Type

from autobyteus.agent.status.manager import AgentStatusManager
from .transition_info import StatusTransitionInfo

logger = logging.getLogger(__name__)

class StatusTransitionDiscoverer:
    """
    A utility class to inspect AgentStatusManager and discover all
    registered status flow transitions.
    """
    _cached_transitions: Optional[List[StatusTransitionInfo]] = None

    @classmethod
    def get_all_transitions(cls, manager_cls: Type[AgentStatusManager] = AgentStatusManager) -> List[StatusTransitionInfo]:
        """
        Inspects the AgentStatusManager class and returns a list of all
        StatusTransitionInfo objects attached to its methods via the @status_transition decorator.
        """
        if cls._cached_transitions is not None:
            return cls._cached_transitions

        logger.debug("Discovering status transitions from AgentStatusManager for the first time.")
        transitions = []
        
        # Inspect all members of the class
        for name, method in inspect.getmembers(manager_cls, predicate=inspect.isfunction):
            # Check for the _transition_info attribute attached by the decorator
            info = getattr(method, '_transition_info', None)
            if isinstance(info, StatusTransitionInfo):
                transitions.append(info)
                
        # Sort for deterministic output (e.g. by target status value)
        transitions.sort(key=lambda t: t.target_status.value)
        
        cls._cached_transitions = transitions
        logger.info(f"Discovered and cached {len(transitions)} status transitions.")
        return transitions

    @classmethod
    def clear_cache(cls) -> None:
        """Clears the cached list of transitions."""
        cls._cached_transitions = None
        logger.info("Cleared cached status transitions.")
