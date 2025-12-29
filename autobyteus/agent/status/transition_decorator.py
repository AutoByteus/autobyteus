# file: autobyteus/autobyteus/agent/phases/transition_decorator.py
import functools
from typing import List, Callable

from .status_enum import AgentStatus
from .transition_info import StatusTransitionInfo

def status_transition(
    source_phases: List[AgentStatus],
    target_phase: AgentStatus,
    description: str
) -> Callable:
    """
    A decorator to annotate methods in AgentStatusManager that cause a status transition.
    
    This decorator does not alter the method's execution. It attaches a
    StatusTransitionInfo object to the method, making the transition discoverable
    via introspection.
    
    Args:
        source_phases: A list of valid source statuses from which this transition can occur.
        target_phase: The status the agent will be in after this transition.
        description: A human-readable description of what causes this transition.
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)

        # Attach the metadata to the function object itself.
        # We sort source phases for consistent representation.
        sorted_sources = tuple(sorted(source_phases, key=lambda p: p.value))
        setattr(wrapper, '_transition_info', StatusTransitionInfo(
            source_phases=sorted_sources,
            target_phase=target_phase,
            description=description,
            triggering_method=func.__name__
        ))
        return wrapper
    return decorator
