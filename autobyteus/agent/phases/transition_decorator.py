# file: autobyteus/autobyteus/agent/phases/transition_decorator.py
import functools
from typing import List, Callable

from .phase_enum import AgentOperationalPhase
from .transition_info import PhaseTransitionInfo

def phase_transition(
    source_phases: List[AgentOperationalPhase],
    target_phase: AgentOperationalPhase,
    description: str
) -> Callable:
    """
    A decorator to annotate methods in AgentPhaseManager that cause a phase transition.
    
    This decorator does not alter the method's execution. It attaches a
    PhaseTransitionInfo object to the method, making the transition discoverable
    via introspection.
    
    Args:
        source_phases: A list of valid source phases from which this transition can occur.
        target_phase: The phase the agent will be in after this transition.
        description: A human-readable description of what causes this transition.
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)

        # Attach the metadata to the function object itself.
        # We sort source phases for consistent representation.
        sorted_sources = tuple(sorted(source_phases, key=lambda p: p.value))
        setattr(wrapper, '_transition_info', PhaseTransitionInfo(
            source_phases=sorted_sources,
            target_phase=target_phase,
            description=description,
            triggering_method=func.__name__
        ))
        return wrapper
    return decorator
