# file: autobyteus/autobyteus/task_management/in_memory_task_plan.py
"""
An in-memory implementation of the BaseTaskPlan.
It tracks task statuses in a simple dictionary and emits events on state changes.
"""
import logging
from typing import Optional, List, Dict, Any
from enum import Enum

from autobyteus.events.event_types import EventType
from .schemas import TaskDefinitionSchema
from .task import Task
from .base_task_plan import BaseTaskPlan, TaskStatus
from .events import TasksCreatedEvent, TaskStatusUpdatedEvent

logger = logging.getLogger(__name__)

class InMemoryTaskPlan(BaseTaskPlan):
    """
    An in-memory, dictionary-based implementation of the TaskPlan that emits
    events on state changes.
    """
    def __init__(self, team_id: str):
        """
        Initializes the InMemoryTaskPlan.
        """
        super().__init__(team_id=team_id)
        self.task_statuses: Dict[str, TaskStatus] = {}
        self._task_map: Dict[str, Task] = {}
        self._id_counter: int = 0
        logger.info(f"InMemoryTaskPlan initialized for team '{self.team_id}'.")
    
    def _generate_next_id(self) -> str:
        self._id_counter += 1
        return f"task_{self._id_counter:04d}"

    def add_tasks(self, task_definitions: List[TaskDefinitionSchema]) -> List[Task]:
        """
        Creates new tasks from definitions, adds them to the plan, and returns the created tasks.
        """
        new_tasks: List[Task] = []
        for task_def in task_definitions:
            new_id = self._generate_next_id()
            task = Task(task_id=new_id, **task_def.model_dump())
            
            self.tasks.append(task)
            self.task_statuses[task.task_id] = TaskStatus.NOT_STARTED
            self._task_map[task.task_id] = task
            new_tasks.append(task)

        self._hydrate_all_dependencies()
        logger.info(f"Team '{self.team_id}': Added {len(new_tasks)} new task(s) to the plan. Emitting TasksCreatedEvent.")
        
        event_payload = TasksCreatedEvent(
            team_id=self.team_id,
            tasks=new_tasks,
        )
        self.emit(EventType.TASK_PLAN_TASKS_CREATED, payload=event_payload)
        return new_tasks

    def add_task(self, task_definition: TaskDefinitionSchema) -> Optional[Task]:
        """
        Creates a single new task from a definition, adds it to the plan, and returns it.
        """
        created_tasks = self.add_tasks([task_definition])
        return created_tasks[0] if created_tasks else None
        
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
                # Case 1: The dependency is already a valid task_id on the plan.
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
        self.emit(EventType.TASK_PLAN_STATUS_UPDATED, payload=event_payload)
        return True

    def get_status_overview(self) -> Dict[str, Any]:
        """
        Returns a serializable dictionary of the plan's current state.
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
