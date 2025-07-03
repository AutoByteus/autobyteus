# file: autobyteus/autobyteus/agent/phases/__init__.py
"""
This package contains components for defining and describing agent operational phases
and their transitions.
"""
from .phase_enum import AgentOperationalPhase
from .transition_info import PhaseTransitionInfo
from .transition_decorator import phase_transition
from .discover import PhaseTransitionDiscoverer
from .manager import AgentPhaseManager

__all__ = [
    "AgentOperationalPhase",
    "PhaseTransitionInfo",
    "phase_transition",
    "PhaseTransitionDiscoverer",
    "AgentPhaseManager",
]
