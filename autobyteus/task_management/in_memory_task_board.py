# file: autobyteus/autobyteus/task_management/in_memory_task_board.py
"""
An in-memory implementation of the BaseTaskBoard.
It tracks task statuses in a simple dictionary and emits events on state changes.
"""
import logging
from typing import Optional, List, Dict, Any
from enum import Enum

from autobyteus.events.event_types import EventType
from .task import Task
from .base_task_board import BaseTaskBoard, TaskStatus
from .events import TasksAddedEvent, TaskStatusUpdatedEvent

logger = logging.getLogger(__name__)

class InMemoryTaskBoard(BaseTaskBoard):
    """
    An in-memory, dictionary-based implementation of the TaskBoard that emits
    events on state changes.
    """
    def __init__(self, team_id: str):
        """
        Initializes the InMemoryTaskBoard.
        """
        super().__init__(team_id=team_id)
        self.task_statuses: Dict[str, TaskStatus] = {}
        self._task_map: Dict[str, Task] = {}
        logger.info(f"InMemoryTaskBoard initialized for team '{self.team_id}'.")

    def add_tasks(self, tasks: List[Task]) -> bool:
        """
        Adds new tasks to the board. This is an additive-only operation.
        """
        for task in tasks:
            self.tasks.append(task)
            self.task_statuses[task.task_id] = TaskStatus.NOT_STARTED
            self._task_map[task.task_id] = task

        self._hydrate_all_dependencies()
        logger.info(f"Team '{self.team_id}': Added {len(tasks)} new task(s) to the board. Emitting TasksAddedEvent.")
        
        event_payload = TasksAddedEvent(
            team_id=self.team_id,
            tasks=tasks,
        )
        self.emit(EventType.TASK_BOARD_TASKS_ADDED, payload=event_payload)
        return True

    def add_task(self, task: Task) -> bool:
        """
        Adds a single new task to the board by wrapping it in a list and calling add_tasks.
        """
        return self.add_tasks([task])
        
    def _hydrate_all_dependencies(self):
        """
        Re-calculates all dependencies to ensure they are all valid task_ids.
        This robustly handles dependencies that are already IDs and those that are names.
        """
        name_to_id_map = {task.task_name: task.task_id for task in self.tasks}
        all_task_ids = set(self._task_map.keys())

        for task in self.tasks:
            if not task.dependencies:
                continue

            resolved_deps = []
            for dep in task.dependencies:
                # Case 1: The dependency is already a valid task_id on the board.
                if dep in all_task_ids:
                    resolved_deps.append(dep)
                # Case 2: The dependency is a task_name that can be resolved.
                elif dep in name_to_id_map:
                    resolved_deps.append(name_to_id_map[dep])
                # Case 3: The dependency is invalid.
                else:
                    logger.warning(f"Team '{self.team_id}': Dependency '{dep}' for task '{task.task_name}' could not be resolved to a known task ID or name.")
            
            task.dependencies = resolved_deps


    def update_task_status(self, task_id: str, status: TaskStatus, agent_name: str) -> bool:
        """
        Updates the status of a specific task and emits an event.
        """
        if task_id not in self.task_statuses:
            logger.warning(f"Team '{self.team_id}': Agent '{agent_name}' attempted to update status for non-existent task_id '{task_id}'.")
            return False
        
        old_status = self.task_statuses.get(task_id, "N/A")
        self.task_statuses[task_id] = status
        log_msg = f"Team '{self.team_id}': Status of task '{task_id}' updated from '{old_status.value if isinstance(old_status, Enum) else old_status}' to '{status.value}' by agent '{agent_name}'."
        logger.info(log_msg)
        
        task = self._task_map.get(task_id)
        task_deliverables = task.file_deliverables if task else None

        event_payload = TaskStatusUpdatedEvent(
            team_id=self.team_id,
            task_id=task_id,
            new_status=status,
            agent_name=agent_name,
            deliverables=task_deliverables
        )
        self.emit(EventType.TASK_BOARD_STATUS_UPDATED, payload=event_payload)
        return True

    def get_status_overview(self) -> Dict[str, Any]:
        """
        Returns a serializable dictionary of the board's current state.
        The overall_goal is now fetched from the context via the converter.
        """
        return {
            "task_statuses": {task_id: status.value for task_id, status in self.task_statuses.items()},
            "tasks": [task.model_dump() for task in self.tasks]
        }

    def get_next_runnable_tasks(self) -> List[Task]:
        """
        Calculates which tasks can be executed now based on dependencies and statuses.
        """
        runnable_tasks: List[Task] = []
        for task_id, status in self.task_statuses.items():
            if status == TaskStatus.NOT_STARTED:
                task = self._task_map.get(task_id)
                if not task: continue
                dependencies = task.dependencies
                if not dependencies:
                    runnable_tasks.append(task)
                    continue
                dependencies_met = all(self.task_statuses.get(dep_id) == TaskStatus.COMPLETED for dep_id in dependencies)
                if dependencies_met:
                    runnable_tasks.append(task)
        
        return runnable_tasks
