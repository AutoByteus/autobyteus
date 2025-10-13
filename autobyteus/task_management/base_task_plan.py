# file: autobyteus/autobyteus/task_management/base_task_plan.py
"""
Defines the abstract interface for a TaskPlan and its related enums.
"""
import logging
from abc import ABC, abstractmethod
from enum import Enum
from typing import Dict, Any, List, Optional

from autobyteus.events.event_emitter import EventEmitter
from .task import Task

logger = logging.getLogger(__name__)

class TaskStatus(str, Enum):
    """Enumerates the possible lifecycle states of a task on the TaskPlan."""
    NOT_STARTED = "not_started"
    QUEUED = "queued"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    BLOCKED = "blocked"
    FAILED = "failed"

    def is_terminal(self) -> bool:
        """Returns True if the status is a final state."""
        return self in {TaskStatus.COMPLETED, TaskStatus.FAILED}

class BaseTaskPlan(ABC, EventEmitter):
    """
    Abstract base class for a TaskPlan.

    This class defines the contract for any component that manages the live state
    of tasks for a team. It is a dynamic plan, not a static document.
    It inherits from EventEmitter to broadcast state changes.
    """

    def __init__(self, team_id: str):
        EventEmitter.__init__(self)
        self.team_id = team_id
        self.tasks: List[Task] = []
        logger.debug(f"BaseTaskPlan initialized for team '{self.team_id}'.")

    @abstractmethod
    def add_tasks(self, tasks: List[Task]) -> bool:
        """
        Adds a list of new tasks to the plan. This is an additive-only operation.
        """
        raise NotImplementedError

    @abstractmethod
    def add_task(self, task: Task) -> bool:
        """
        Adds a single new task to the plan.
        """
        raise NotImplementedError

    @abstractmethod
    def update_task_status(self, task_id: str, status: TaskStatus, agent_name: str) -> bool:
        """
        Updates the status of a specific task.
        """
        raise NotImplementedError

    @abstractmethod
    def get_status_overview(self) -> Dict[str, Any]:
        """
        Returns a serializable dictionary of the plan's current state.
        """
        raise NotImplementedError

    @abstractmethod
    def get_next_runnable_tasks(self) -> List[Task]:
        """
        Calculates which tasks can be executed now based on dependencies and statuses.
        """
        raise NotImplementedError
