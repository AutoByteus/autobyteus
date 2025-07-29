# file: autobyteus/autobyteus/workflow/phases/workflow_operational_phase.py
from enum import Enum

class WorkflowOperationalPhase(str, Enum):
    """Defines the operational phases of an AgenticWorkflow."""
    UNINITIALIZED = "uninitialized"
    BOOTSTRAPPING = "bootstrapping"
    IDLE = "idle"
    PROCESSING = "processing"
    SHUTTING_DOWN = "shutting_down"
    SHUTDOWN_COMPLETE = "shutdown_complete"
    ERROR = "error"

    def is_terminal(self) -> bool:
        """Checks if the phase is a terminal state."""
        return self in [WorkflowOperationalPhase.SHUTDOWN_COMPLETE, WorkflowOperationalPhase.ERROR]

    def __str__(self) -> str:
        return self.value
