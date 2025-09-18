# file: autobyteus/autobyteus/task_management/events.py
"""
Defines the Pydantic models for events emitted by a TaskBoard.
"""
from typing import List, Optional
from pydantic import BaseModel

from autobyteus.task_management.task import Task
from autobyteus.task_management.base_task_board import TaskStatus
from .deliverable import FileDeliverable

class BaseTaskBoardEvent(BaseModel):
    """Base class for all task board events."""
    team_id: str

class TasksAddedEvent(BaseTaskBoardEvent):
    """
    Payload for when one or more tasks are added to the board.
    """
    tasks: List[Task]

class TaskStatusUpdatedEvent(BaseTaskBoardEvent):
    """Payload for when a task's status is updated."""
    task_id: str
    new_status: TaskStatus
    agent_name: str
    deliverables: Optional[List[FileDeliverable]] = None
