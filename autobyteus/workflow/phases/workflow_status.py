# file: autobyteus/autobyteus/workflow/phases/workflow_status.py
from enum import Enum

class WorkflowStatus(str, Enum):
    """Defines the operational status of an AgenticWorkflow."""
    UNINITIALIZED = "uninitialized"
    BOOTSTRAPPING = "bootstrapping"
    IDLE = "idle"
    PROCESSING = "processing"
    SHUTTING_DOWN = "shutting_down"
    SHUTDOWN_COMPLETE = "shutdown_complete"
    ERROR = "error"

    def is_terminal(self) -> bool:
        """Checks if the status is a terminal state."""
        return self in [WorkflowStatus.SHUTDOWN_COMPLETE, WorkflowStatus.ERROR]

    def __str__(self) -> str:
        return self.value
