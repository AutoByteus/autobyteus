# file: autobyteus/autobyteus/task_management/__init__.py
"""
This package defines components for task management and state tracking,
including task plans and live task boards. It is designed to be a general-purpose
module usable by various components, such as agents or agent teams.
"""
from .task_plan import TaskPlan, Task
from .schemas import (TaskPlanDefinition, TaskDefinition, TaskStatusReport,
                      TaskStatusReportItem)
from .base_task_board import BaseTaskBoard, TaskStatus
from .in_memory_task_board import InMemoryTaskBoard
from .artifacts import ArtifactManifest, ArtifactState, ArtifactType
from .tools import GetTaskBoardStatus, PublishTaskPlan, UpdateTaskStatus, ManageArtifact
from .converters import TaskBoardConverter, TaskPlanConverter

# For convenience, we can alias InMemoryTaskBoard as the default TaskBoard.
# This allows other parts of the code to import `TaskBoard` without needing
# to know the specific implementation being used by default.
TaskBoard = InMemoryTaskBoard

__all__ = [
    "TaskPlan",
    "Task",
    "TaskPlanDefinition",
    "TaskDefinition",
    "TaskStatusReport",
    "TaskStatusReportItem",
    "BaseTaskBoard",
    "TaskStatus",
    "InMemoryTaskBoard",
    "TaskBoard",  # Exposing the alias
    "ArtifactManifest",
    "ArtifactState",
    "ArtifactType",
    "GetTaskBoardStatus",
    "PublishTaskPlan",
    "UpdateTaskStatus",
    "ManageArtifact",
    "TaskBoardConverter",
    "TaskPlanConverter",
]
