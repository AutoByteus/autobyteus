"""
Defines the data models for a file deliverable.
"""
import datetime
from pydantic import BaseModel, Field

class FileDeliverable(BaseModel):
    """
    Represents the full, internal record of a file deliverable once it has been
    submitted and attached to a task.
    """
    file_path: str
    summary: str
    author_agent_name: str
    timestamp: datetime.datetime = Field(default_factory=datetime.datetime.utcnow)
