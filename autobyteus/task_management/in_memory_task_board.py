# file: autobyteus/autobyteus/task_management/in_memory_task_board.py
"""
An in-memory implementation of the BaseTaskBoard.
It tracks task statuses in a simple dictionary.
"""
import logging
from typing import Optional, List, Dict, Any
from enum import Enum

from .task_plan import TaskPlan, Task
from .base_task_board import BaseTaskBoard, TaskStatus

logger = logging.getLogger(__name__)

class InMemoryTaskBoard(BaseTaskBoard):
    """
    An in-memory, dictionary-based implementation of the TaskBoard.
    This implementation is suitable for single-process, non-persistent agent teams.
    """
    def __init__(self, team_id: str):
        """
        Initializes the InMemoryTaskBoard.
        """
        super().__init__(team_id)
        self.current_plan: Optional[TaskPlan] = None
        self.task_statuses: Dict[str, TaskStatus] = {}
        self._task_map: Dict[str, Task] = {}
        logger.info(f"InMemoryTaskBoard initialized for team '{self.team_id}'.")

    def load_task_plan(self, plan: TaskPlan) -> bool:
        """
        Loads a new plan onto the board, resetting its state.

        Args:
            plan: The TaskPlan to load.

        Returns:
            True if the plan was loaded successfully, False otherwise.
        """
        if not isinstance(plan, TaskPlan):
            logger.error(f"Team '{self.team_id}': Failed to load task plan. Provided object is not a TaskPlan.")
            return False

        self.current_plan = plan
        self.task_statuses = {task.task_id: TaskStatus.NOT_STARTED for task in plan.tasks}
        self._task_map = {task.task_id: task for task in plan.tasks}
        
        logger.info(f"Team '{self.team_id}': New TaskPlan '{plan.plan_id}' loaded onto InMemoryTaskBoard. {len(plan.tasks)} tasks set to NOT_STARTED.")
        return True

    def update_task_status(self, task_id: str, status: TaskStatus, agent_name: str, produced_artifact_ids: Optional[List[str]] = None) -> bool:
        """
        Updates the status of a specific task and optionally links produced artifacts.

        Args:
            task_id: The ID of the task to update.
            status: The new status for the task.
            agent_name: The name of the agent reporting the status change.
            produced_artifact_ids: An optional list of artifact IDs created by this task.

        Returns:
            True if the status was updated, False if the task_id is invalid.
        """
        if task_id not in self.task_statuses:
            logger.warning(f"Team '{self.team_id}': Agent '{agent_name}' attempted to update status for non-existent task_id '{task_id}'.")
            return False
        
        old_status = self.task_statuses.get(task_id, "N/A")
        self.task_statuses[task_id] = status
        log_msg = f"Team '{self.team_id}': Status of task '{task_id}' updated from '{old_status.value if isinstance(old_status, Enum) else old_status}' to '{status.value}' by agent '{agent_name}'."

        # NEW: If the task is completed and artifacts are provided, link them.
        if status == TaskStatus.COMPLETED and produced_artifact_ids:
            task = self._task_map.get(task_id)
            if task:
                # Append to avoid overwriting if somehow updated in parts (unlikely but safe).
                # A better approach is to just set it.
                task.produced_artifact_ids = list(set(task.produced_artifact_ids + produced_artifact_ids))
                log_msg += f" Linked artifact IDs: {produced_artifact_ids}."
            else:
                logger.error(f"Team '{self.team_id}': Could not find task '{task_id}' in internal map to link artifacts.")

        logger.info(log_msg)
        return True

    def get_status_overview(self) -> Dict[str, Any]:
        """
        Returns a serializable dictionary of the board's current state.

        Returns:
            A dictionary containing the plan ID, goal, and task statuses.
        """
        if not self.current_plan:
            return {
                "plan_id": None,
                "overall_goal": None,
                "task_statuses": {},
                "tasks": []
            }
        
        return {
            "plan_id": self.current_plan.plan_id,
            "overall_goal": self.current_plan.overall_goal,
            "task_statuses": {task_id: status.value for task_id, status in self.task_statuses.items()},
            "tasks": [task.model_dump() for task in self.current_plan.tasks] # Include full task data
        }

    def get_next_runnable_tasks(self) -> List[Task]:
        """
        Calculates which tasks can be executed now based on dependencies and statuses.

        A task is runnable if:
        1. Its status is NOT_STARTED.
        2. All of its dependencies have a status of COMPLETED.

        Returns:
            A list of Task objects that are ready to be run.
        """
        runnable_tasks: List[Task] = []
        if not self.current_plan:
            logger.debug(f"Team '{self.team_id}': Cannot get runnable tasks, no plan is loaded.")
            return runnable_tasks

        for task_id, status in self.task_statuses.items():
            if status == TaskStatus.NOT_STARTED:
                task = self._task_map.get(task_id)
                if not task:
                    continue

                dependencies = task.dependencies
                if not dependencies:
                    runnable_tasks.append(task)
                    continue

                dependencies_met = all(
                    self.task_statuses.get(dep_id) == TaskStatus.COMPLETED
                    for dep_id in dependencies
                )

                if dependencies_met:
                    runnable_tasks.append(task)

        if runnable_tasks:
            logger.info(f"Team '{self.team_id}': Found {len(runnable_tasks)} runnable tasks: {[t.task_id for t in runnable_tasks]}")
        else:
            logger.debug(f"Team '{self.team_id}': No runnable tasks found at this time.")

        return runnable_tasks
