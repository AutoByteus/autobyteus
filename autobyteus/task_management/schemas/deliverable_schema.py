# file: autobyteus/autobyteus/task_management/schemas/deliverable_schema.py
"""
Defines the Pydantic schema for submitting a file deliverable.
"""
from pydantic import BaseModel, Field
from autobyteus.task_management.deliverable import DeliverableStatus

class FileDeliverableSchema(BaseModel):
    """
    A Pydantic model representing the arguments for submitting a single
    file deliverable. This is used as an input schema for tools.
    """
    file_path: str = Field(..., description="The relative path to the file being submitted.")
    status: DeliverableStatus = Field(..., description="The status of the submission ('new' or 'updated').")
    summary: str = Field(..., description="A summary of the work done on this file.")
