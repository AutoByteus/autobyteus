# file: autobyteus/autobyteus/task_management/in_memory_task_board.py
"""
An in-memory implementation of the BaseTaskBoard.
It tracks task statuses in a simple dictionary and emits events on state changes.
"""
import logging
from typing import Optional, List, Dict, Any
from enum import Enum

from autobyteus.events.event_types import EventType
from .task_plan import TaskPlan, Task
from .base_task_board import BaseTaskBoard, TaskStatus
from .events import TaskPlanPublishedEvent, TaskStatusUpdatedEvent

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
        # BaseTaskBoard now handles EventEmitter initialization
        super().__init__(team_id=team_id)
        self.current_plan: Optional[TaskPlan] = None
        self.task_statuses: Dict[str, TaskStatus] = {}
        self._task_map: Dict[str, Task] = {}
        logger.info(f"InMemoryTaskBoard initialized for team '{self.team_id}'.")

    def load_task_plan(self, plan: TaskPlan) -> bool:
        """
        Loads a new plan onto the board, resetting its state and emitting an event.
        """
        if not isinstance(plan, TaskPlan):
            logger.error(f"Team '{self.team_id}': Failed to load task plan. Provided object is not a TaskPlan.")
            return False

        self.current_plan = plan
        self.task_statuses = {task.task_id: TaskStatus.NOT_STARTED for task in plan.tasks}
        self._task_map = {task.task_id: task for task in plan.tasks}
        
        logger.info(f"Team '{self.team_id}': New TaskPlan '{plan.plan_id}' loaded. Emitting event.")
        
        # Emit event
        event_payload = TaskPlanPublishedEvent(
            team_id=self.team_id,
            plan_id=plan.plan_id,
            plan=plan
        )
        self.emit(EventType.TASK_BOARD_PLAN_PUBLISHED, payload=event_payload)
        
        return True

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
        
        # Find the task to get its deliverables for the event payload
        task = self._task_map.get(task_id)
        task_deliverables = task.file_deliverables if task else None

        # Emit event
        event_payload = TaskStatusUpdatedEvent(
            team_id=self.team_id,
            plan_id=self.current_plan.plan_id if self.current_plan else None,
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
            "tasks": [task.model_dump() for task in self.current_plan.tasks]
        }

    def get_next_runnable_tasks(self) -> List[Task]:
        """
        Calculates which tasks can be executed now based on dependencies and statuses.
        """
        runnable_tasks: List[Task] = []
        if not self.current_plan:
            return runnable_tasks

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
