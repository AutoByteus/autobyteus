# file: autobyteus/autobyteus/task_management/schemas/deliverable_schema.py
"""
Defines the Pydantic schema for submitting a file deliverable.
"""
from pydantic import BaseModel, Field

class FileDeliverableSchema(BaseModel):
    """
    A Pydantic model representing the arguments for submitting a single
    file deliverable. This is used as an input schema for tools.
    """
    file_path: str = Field(..., description="The relative path to the file being submitted.")
    summary: str = Field(..., description="A summary of the work done on this file, explaining what is new or what was updated.")
