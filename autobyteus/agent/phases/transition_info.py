# file: autobyteus/autobyteus/agent/phases/transition_info.py
import logging
from dataclasses import dataclass
from typing import List, Tuple

from .phase_enum import AgentOperationalPhase

logger = logging.getLogger(__name__)

@dataclass(frozen=True)
class PhaseTransitionInfo:
    """
    A dataclass representing a valid, discoverable phase transition.
    
    This object provides the necessary metadata for users to understand what
    kinds of phase hooks they can create.
    
    Attributes:
        source_phases: A list of possible source phases for this transition.
        target_phase: The single target phase for this transition.
        description: A human-readable description of when this transition occurs.
        triggering_method: The name of the method in AgentPhaseManager that triggers this.
    """
    source_phases: Tuple[AgentOperationalPhase, ...]
    target_phase: AgentOperationalPhase
    description: str
    triggering_method: str

    def __repr__(self) -> str:
        sources = ", ".join(f"'{p.value}'" for p in self.source_phases)
        return (f"<PhaseTransitionInfo sources=[{sources}] -> "
                f"target='{self.target_phase.value}' "
                f"triggered_by='{self.triggering_method}'>")
