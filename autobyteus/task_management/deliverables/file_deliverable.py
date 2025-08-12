# file: autobyteus/autobyteus/task_management/deliverables/file_deliverable.py
"""
Defines the data models for a file deliverable.
"""
import datetime
from pydantic import BaseModel, Field

from .deliverable_status import DeliverableStatus

class FileDeliverableSchema(BaseModel):
    """
    A Pydantic model representing the arguments for submitting a single
    file deliverable. This is used as an input schema for tools.
    """
    file_path: str = Field(..., description="The relative path to the file being submitted.")
    status: DeliverableStatus = Field(..., description="The status of the submission ('new' or 'updated').")
    summary: str = Field(..., description="A summary of the work done on this file.")

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
