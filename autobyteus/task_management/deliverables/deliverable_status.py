# file: autobyteus/autobyteus/task_management/deliverables/deliverable_status.py
"""
Defines the status for a submitted file deliverable.
"""
from enum import Enum

class DeliverableStatus(str, Enum):
    """Enumerates the status of a file deliverable submission."""
    NEW = "new"
    UPDATED = "updated"

    def __str__(self) -> str:
        return self.value
