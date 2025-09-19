# file: autobyteus/autobyteus/task_management/schemas/task_status_report.py
"""
Defines the Pydantic models for LLM-friendly status reports.

These models are designed to be returned by tools to the LLM, providing a
clear and consistent structure that mirrors the input schemas (like TaskPlanDefinitionSchema)
but includes dynamic state information (like task status).
"""
from typing import List, Optional
from pydantic import BaseModel, Field

from autobyteus.task_management.base_task_board import TaskStatus
from autobyteus.task_management.deliverable import FileDeliverable

class TaskStatusReportItemSchema(BaseModel):
    """Represents the status of a single task in an LLM-friendly format."""
    task_name: str = Field(..., description="The unique, descriptive name for this task.")
    assignee_name: str = Field(..., description="The name of the agent or sub-team assigned to this task.")
    description: str = Field(..., description="A detailed description of the task.")
    dependencies: List[str] = Field(..., description="A list of 'task_name' values for tasks that must be completed first.")
    status: TaskStatus = Field(..., description="The current status of this task.")
    file_deliverables: List[FileDeliverable] = Field(default_factory=list, description="A list of files submitted as deliverables for this task.")

class TaskStatusReportSchema(BaseModel):
    """Represents a full task board status report in an LLM-friendly format."""
    tasks: List[TaskStatusReportItemSchema] = Field(..., description="The list of tasks and their current statuses.")
