# file: autobyteus/autobyteus/task_management/__init__.py
"""
This package defines components for task management and state tracking,
including task plans and live task boards. It is designed to be a general-purpose
module usable by various components, such as agents or agent teams.
"""
from .task import Task
from .schemas import (TasksDefinitionSchema, TaskDefinitionSchema, TaskStatusReportSchema,
                      TaskStatusReportItemSchema, FileDeliverableSchema, ToDoDefinitionSchema, ToDosDefinitionSchema)
from .base_task_board import BaseTaskBoard, TaskStatus
from .in_memory_task_board import InMemoryTaskBoard
from .deliverable import FileDeliverable
from .tools import (
    GetTaskBoardStatus,
    PublishTasks,
    PublishTask,
    UpdateTaskStatus,
    AssignTaskTo,
    GetMyTasks,
    CreateToDoList,
    AddToDo,
    GetToDoList,
    UpdateToDoStatus as UpdateToDoStatusTool,
)
from .converters import TaskBoardConverter
from .events import BaseTaskBoardEvent, TasksAddedEvent, TaskStatusUpdatedEvent
from .todo import ToDo, ToDoStatus
from .todo_list import ToDoList

# For convenience, we can alias InMemoryTaskBoard as the default TaskBoard.
# This allows other parts of the code to import `TaskBoard` without needing
# to know the specific implementation being used by default.
TaskBoard = InMemoryTaskBoard

__all__ = [
    "Task",
    "TasksDefinitionSchema",
    "TaskDefinitionSchema",
    "TaskStatusReportSchema",
    "TaskStatusReportItemSchema",
    "FileDeliverableSchema",
    "ToDoDefinitionSchema",
    "ToDosDefinitionSchema",
    "BaseTaskBoard",
    "TaskStatus",
    "InMemoryTaskBoard",
    "TaskBoard",  # Exposing the alias
    "FileDeliverable",
    "GetTaskBoardStatus",
    "PublishTasks",
    "PublishTask",
    "UpdateTaskStatus",
    "AssignTaskTo",
    "GetMyTasks",
    "CreateToDoList",
    "AddToDo",
    "GetToDoList",
    "UpdateToDoStatusTool",
    "TaskBoardConverter",
    "BaseTaskBoardEvent",
    "TasksAddedEvent",
    "TaskStatusUpdatedEvent",
    "ToDo",
    "ToDoStatus",
    "ToDoList",
]
