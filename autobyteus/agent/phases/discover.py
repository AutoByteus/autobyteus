# file: autobyteus/autobyteus/agent/phases/discover.py
import inspect
import logging
from typing import List, Optional

from autobyteus.agent.context.agent_phase_manager import AgentPhaseManager
from .transition_info import PhaseTransitionInfo

logger = logging.getLogger(__name__)

class PhaseTransitionDiscoverer:
    """
    A utility class to discover all valid phase transitions within the system.
    
    It works by introspecting the AgentPhaseManager and finding methods
    that have been decorated with the `@phase_transition` decorator.
    """
    _cached_transitions: Optional[List[PhaseTransitionInfo]] = None

    @classmethod
    def discover(cls) -> List[PhaseTransitionInfo]:
        """
        Discovers and returns a list of all possible phase transitions.
        
        The result is cached after the first call for performance.
        
        Returns:
            A list of PhaseTransitionInfo objects, each describing a valid transition.
        """
        if cls._cached_transitions is not None:
            return cls._cached_transitions

        logger.debug("Discovering phase transitions from AgentPhaseManager for the first time.")
        transitions = []
        for name, method in inspect.getmembers(AgentPhaseManager, predicate=inspect.isfunction):
            if hasattr(method, '_transition_info'):
                info = getattr(method, '_transition_info')
                if isinstance(info, PhaseTransitionInfo):
                    transitions.append(info)
        
        # Sort for deterministic output
        transitions.sort(key=lambda t: (t.target_phase.value, t.triggering_method))
        
        cls._cached_transitions = transitions
        logger.info(f"Discovered and cached {len(transitions)} phase transitions.")
        return transitions

    @classmethod
    def clear_cache(cls) -> None:
        """Clears the cached list of transitions."""
        cls._cached_transitions = None
        logger.info("Cleared cached phase transitions.")
