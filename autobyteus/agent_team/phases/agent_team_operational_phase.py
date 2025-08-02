# file: autobyteus/autobyteus/agent_team/phases/agent_team_operational_phase.py
from enum import Enum

class AgentTeamOperationalPhase(str, Enum):
    """Defines the operational phases of an AgentTeam."""
    UNINITIALIZED = "uninitialized"
    BOOTSTRAPPING = "bootstrapping"
    IDLE = "idle"
    PROCESSING = "processing"
    SHUTTING_DOWN = "shutting_down"
    SHUTDOWN_COMPLETE = "shutdown_complete"
    ERROR = "error"

    def is_terminal(self) -> bool:
        """Checks if the phase is a terminal state."""
        return self in [AgentTeamOperationalPhase.SHUTDOWN_COMPLETE, AgentTeamOperationalPhase.ERROR]

    def __str__(self) -> str:
        return self.value
