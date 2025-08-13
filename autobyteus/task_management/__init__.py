# file: autobyteus/autobyteus/task_management/__init__.py
"""
This package defines components for task management and state tracking,
including task plans and live task boards. It is designed to be a general-purpose
module usable by various components, such as agents or agent teams.
"""
from .task_plan import TaskPlan, Task
from .schemas import (TaskPlanDefinitionSchema, TaskDefinitionSchema, TaskStatusReportSchema,
                      TaskStatusReportItemSchema, FileDeliverableSchema)
from .base_task_board import BaseTaskBoard, TaskStatus
from .in_memory_task_board import InMemoryTaskBoard
from .deliverable import FileDeliverable
from .tools import GetTaskBoardStatus, PublishTaskPlan, UpdateTaskStatus
from .converters import TaskBoardConverter, TaskPlanConverter
from .events import BaseTaskBoardEvent, TaskPlanPublishedEvent, TaskStatusUpdatedEvent

# For convenience, we can alias InMemoryTaskBoard as the default TaskBoard.
# This allows other parts of the code to import `TaskBoard` without needing
# to know the specific implementation being used by default.
TaskBoard = InMemoryTaskBoard

__all__ = [
    "TaskPlan",
    "Task",
    "TaskPlanDefinitionSchema",
    "TaskDefinitionSchema",
    "TaskStatusReportSchema",
    "TaskStatusReportItemSchema",
    "FileDeliverableSchema",
    "BaseTaskBoard",
    "TaskStatus",
    "InMemoryTaskBoard",
    "TaskBoard",  # Exposing the alias
    "FileDeliverable",
    "GetTaskBoardStatus",
    "PublishTaskPlan",
    "UpdateTaskStatus",
    "TaskBoardConverter",
    "TaskPlanConverter",
    "BaseTaskBoardEvent",
    "TaskPlanPublishedEvent",
    "TaskStatusUpdatedEvent",
]
