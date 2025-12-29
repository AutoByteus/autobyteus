# file: autobyteus/autobyteus/agent/status/transition_info.py
import logging
from dataclasses import dataclass
from typing import List, Tuple

from .status_enum import AgentStatus

logger = logging.getLogger(__name__)

@dataclass(frozen=True)
class StatusTransitionInfo:
    """
    A dataclass representing a valid, discoverable status transition.
    
    This object provides the necessary metadata for users to understand what
    kinds of status (lifecycle) hooks they can create.
    
    Attributes:
        source_statuses: A list of possible source statuses for this transition.
        target_status: The single target status for this transition.
        description: A human-readable description of when this transition occurs.
        triggering_method: The name of the method in AgentStatusManager that triggers this.
    """
    source_statuses: Tuple[AgentStatus, ...]
    target_status: AgentStatus
    description: str
    triggering_method: str

    def __repr__(self) -> str:
        sources = ", ".join(f"'{p.value}'" for p in self.source_statuses)
        return (f"<StatusTransitionInfo sources=[{sources}] -> "
                f"target='{self.target_status.value}' "
                f"triggered_by='{self.triggering_method}'>")
