# file: autobyteus/autobyteus/task_management/events.py
"""
Defines the Pydantic models for events emitted by a TaskBoard.
"""
from typing import List, Optional
from pydantic import BaseModel

from autobyteus.task_management.task_plan import TaskPlan
from autobyteus.task_management.base_task_board import TaskStatus

class BaseTaskBoardEvent(BaseModel):
    """Base class for all task board events."""
    team_id: str
    plan_id: Optional[str]

class TaskPlanPublishedEvent(BaseTaskBoardEvent):
    """Payload for when a new task plan is published to the board."""
    plan: TaskPlan

class TaskStatusUpdatedEvent(BaseTaskBoardEvent):
    """Payload for when a task's status is updated."""
    task_id: str
    new_status: TaskStatus
    agent_name: str
