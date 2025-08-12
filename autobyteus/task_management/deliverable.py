# file: autobyteus/autobyteus/task_management/deliverable.py
"""
Defines the core data models for a deliverable and its status.
"""
import datetime
from enum import Enum
from pydantic import BaseModel, Field

class DeliverableStatus(str, Enum):
    """Enumerates the status of a file deliverable submission."""
    NEW = "new"
    UPDATED = "updated"

    def __str__(self) -> str:
        return self.value

class FileDeliverable(BaseModel):
    """
    Represents the full, internal record of a file deliverable once it has been
    submitted and attached to a task.
    """
    file_path: str
    status: DeliverableStatus
    summary: str
    author_agent_name: str
    timestamp: datetime.datetime = Field(default_factory=datetime.datetime.utcnow)
