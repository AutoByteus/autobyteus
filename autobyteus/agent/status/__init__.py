# file: autobyteus/autobyteus/agent/phases/__init__.py
"""
This package contains components for defining and describing agent operational phases
and their transitions.
"""
from .status_enum import AgentStatus
from .transition_info import StatusTransitionInfo
from .transition_decorator import status_transition
from .discover import StatusTransitionDiscoverer
from .manager import AgentStatusManager

__all__ = [
    "AgentStatus",
    "StatusTransitionInfo",
    "status_transition",
    "StatusTransitionDiscoverer",
    "AgentStatusManager",
]
