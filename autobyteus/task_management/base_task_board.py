# file: autobyteus/autobyteus/task_management/base_task_board.py
"""
Defines the abstract interface for a TaskBoard and its related enums.
"""
import logging
from abc import ABC, abstractmethod
from enum import Enum
from typing import Dict, Any, List, Optional

from autobyteus.events.event_emitter import EventEmitter
from .task_plan import Task, TaskPlan

logger = logging.getLogger(__name__)

class TaskStatus(str, Enum):
    """Enumerates the possible lifecycle states of a task on the TaskBoard."""
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    BLOCKED = "blocked"
    FAILED = "failed"

    def is_terminal(self) -> bool:
        """Returns True if the status is a final state."""
        return self in {TaskStatus.COMPLETED, TaskStatus.FAILED}

class BaseTaskBoard(ABC, EventEmitter):
    """
    Abstract base class for a TaskBoard.

    This class defines the contract for any component that manages the live state
    of a TaskPlan. Implementations could be in-memory, database-backed, or
    connected to external services like JIRA. It inherits from EventEmitter to
    broadcast state changes.
    """

    def __init__(self, team_id: str):
        EventEmitter.__init__(self)
        self.team_id = team_id
        logger.debug(f"BaseTaskBoard initialized for team '{self.team_id}'.")

    @abstractmethod
    def load_task_plan(self, plan: TaskPlan) -> bool:
        """
        Loads a new plan onto the board, resetting its state.
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
        Returns a serializable dictionary of the board's current state.
        """
        raise NotImplementedError

    @abstractmethod
    def get_next_runnable_tasks(self) -> List[Task]:
        """
        Calculates which tasks can be executed now based on dependencies and statuses.
        """
        raise NotImplementedError
