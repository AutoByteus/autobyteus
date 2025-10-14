# file: autobyteus/autobyteus/task_management/events.py
"""
Defines the Pydantic models for events emitted by a TaskPlan.
"""
from typing import List, Optional
from pydantic import BaseModel

from autobyteus.task_management.task import Task
from autobyteus.task_management.base_task_plan import TaskStatus
from .deliverable import FileDeliverable

class BaseTaskPlanEvent(BaseModel):
    """Base class for all task plan events."""
    team_id: str

class TasksCreatedEvent(BaseTaskPlanEvent):
    """
    Payload for when one or more tasks are created in the plan.
    """
    tasks: List[Task]

class TaskStatusUpdatedEvent(BaseTaskPlanEvent):
    """Payload for when a task's status is updated."""
    task_id: str
    new_status: TaskStatus
    agent_name: str
    deliverables: Optional[List[FileDeliverable]] = None
