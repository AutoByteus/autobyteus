# file: autobyteus/autobyteus/task_management/__init__.py
"""
This package defines components for task management and state tracking,
including task plans and live plan execution tracking. It is designed to be a
general-purpose module usable by various components, such as agents or agent teams.
"""
from .task import Task
from .schemas import (TasksDefinitionSchema, TaskDefinitionSchema, TaskStatusReportSchema,
                      TaskStatusReportItemSchema, FileDeliverableSchema, ToDoDefinitionSchema, ToDosDefinitionSchema)
from .base_task_plan import BaseTaskPlan, TaskStatus
from .in_memory_task_plan import InMemoryTaskPlan
from .deliverable import FileDeliverable
from .tools import (
    GetTaskPlanStatus,
    CreateTasks,
    CreateTask,
    UpdateTaskStatus,
    AssignTaskTo,
    GetMyTasks,
    CreateToDoList,
    AddToDo,
    GetToDoList,
    UpdateToDoStatus as UpdateToDoStatusTool,
)
from .converters import TaskPlanConverter
from .events import BaseTaskPlanEvent, TasksCreatedEvent, TaskStatusUpdatedEvent
from .todo import ToDo, ToDoStatus
from .todo_list import ToDoList

# For convenience, we can alias InMemoryTaskPlan as the default TaskPlan.
# This allows other parts of the code to import `TaskPlan` without needing
# to know the specific implementation being used by default.
TaskPlan = InMemoryTaskPlan

__all__ = [
    "Task",
    "TasksDefinitionSchema",
    "TaskDefinitionSchema",
    "TaskStatusReportSchema",
    "TaskStatusReportItemSchema",
    "FileDeliverableSchema",
    "ToDoDefinitionSchema",
    "ToDosDefinitionSchema",
    "BaseTaskPlan",
    "TaskStatus",
    "InMemoryTaskPlan",
    "TaskPlan",  # Exposing the alias
    "FileDeliverable",
    "GetTaskPlanStatus",
    "CreateTasks",
    "CreateTask",
    "UpdateTaskStatus",
    "AssignTaskTo",
    "GetMyTasks",
    "CreateToDoList",
    "AddToDo",
    "GetToDoList",
    "UpdateToDoStatusTool",
    "TaskPlanConverter",
    "BaseTaskPlanEvent",
    "TasksCreatedEvent",
    "TaskStatusUpdatedEvent",
    "ToDo",
    "ToDoStatus",
    "ToDoList",
]
