from enum import Enum

class AgentTeamStatus(str, Enum):
    """Defines the operational status of an AgentTeam."""
    UNINITIALIZED = "uninitialized"
    BOOTSTRAPPING = "bootstrapping"
    IDLE = "idle"
    PROCESSING = "processing"
    SHUTTING_DOWN = "shutting_down"
    SHUTDOWN_COMPLETE = "shutdown_complete"
    ERROR = "error"

    def is_terminal(self) -> bool:
        """Checks if the status is a terminal state."""
        return self in [AgentTeamStatus.SHUTDOWN_COMPLETE, AgentTeamStatus.ERROR]

    def __str__(self) -> str:
        return self.value
