# file: autobyteus/autobyteus/agent_team/task_notification/system_event_driven_agent_task_notifier.py
import asyncio
import logging
from typing import Set, Any, TYPE_CHECKING, List, Union

from autobyteus.events.event_types import EventType
from autobyteus.agent_team.events import ProcessUserMessageEvent
from autobyteus.agent.message import AgentInputUserMessage
from autobyteus.task_management.events import TasksAddedEvent, TaskStatusUpdatedEvent
from autobyteus.task_management.base_task_board import TaskStatus
from autobyteus.task_management.task import Task

if TYPE_CHECKING:
    from autobyteus.task_management.base_task_board import BaseTaskBoard
    from autobyteus.agent_team.context.team_manager import TeamManager

logger = logging.getLogger(__name__)

class SystemEventDrivenAgentTaskNotifier:
    """
    An internal component that monitors a TaskBoard and automatically sends
    notifications to agents when their assigned tasks become runnable.
    """
    def __init__(self, task_board: 'BaseTaskBoard', team_manager: 'TeamManager'):
        """
        Initializes the SystemEventDrivenAgentTaskNotifier.

        Args:
            task_board: The team's shared task board instance.
            team_manager: The team's manager for submitting notification events.
        """
        if not task_board or not team_manager:
            raise ValueError("TaskBoard and TeamManager are required for the notifier.")
            
        self._task_board = task_board
        self._team_manager = team_manager
        self._dispatched_task_ids: Set[str] = set()
        logger.info(f"SystemEventDrivenAgentTaskNotifier initialized for team '{self._team_manager.team_id}'.")

    def start_monitoring(self):
        """
        Subscribes to task board events to begin monitoring for runnable tasks.
        This should be called once during the agent team's bootstrap process.
        """
        self._task_board.subscribe(EventType.TASK_BOARD_TASKS_ADDED, self._handle_tasks_added)
        self._task_board.subscribe(EventType.TASK_BOARD_STATUS_UPDATED, self._handle_status_updated)
        logger.info(f"Team '{self._team_manager.team_id}': Task notifier is now monitoring TaskBoard events.")
    
    async def _handle_tasks_added(self, payload: TasksAddedEvent, **kwargs):
        """Handles the event for tasks being added to the board."""
        logger.info(f"Team '{self._team_manager.team_id}': {len(payload.tasks)} tasks added to board. Checking if they are runnable.")
        await self._scan_and_notify_tasks(payload.tasks)

    async def _handle_status_updated(self, payload: TaskStatusUpdatedEvent, **kwargs):
        """Handles the event for a task's status changing."""
        if payload.new_status == TaskStatus.COMPLETED:
            logger.info(f"Team '{self._team_manager.team_id}': Task '{payload.task_id}' completed. Checking for newly unblocked dependent tasks.")
            await self._check_and_notify_dependent_tasks(payload.task_id)

    async def _scan_and_notify_tasks(self, tasks_to_check: List[Task]):
        """Scans a specific list of tasks to see if they are runnable and notifies if so."""
        all_task_statuses = self._task_board.task_statuses
        for task in tasks_to_check:
            if task.task_id not in self._dispatched_task_ids and all_task_statuses.get(task.task_id) == TaskStatus.NOT_STARTED:
                dependencies_met = all(
                    all_task_statuses.get(dep_id) == TaskStatus.COMPLETED for dep_id in task.dependencies
                )
                if dependencies_met:
                    await self._dispatch_notification_for_task(task)

    async def _check_and_notify_dependent_tasks(self, completed_task_id: str):
        """
        Finds tasks that depend on the completed task and notifies their assignees
        if all of their other dependencies are also met.
        """
        all_tasks = self._task_board.tasks
        task_statuses = self._task_board.task_statuses

        for child_task in all_tasks:
            # Dependencies are now IDs, so we check against the completed task's ID
            if completed_task_id in child_task.dependencies:
                all_deps_met = all(
                    task_statuses.get(dep_id) == TaskStatus.COMPLETED for dep_id in child_task.dependencies
                )
                
                if all_deps_met and child_task.task_id not in self._dispatched_task_ids:
                    await self._dispatch_notification_for_task(child_task)
    
    async def _dispatch_notification_for_task(self, task: Task):
        """
        Constructs and sends a context-rich notification for a single runnable task
        by treating it as a user message to trigger the full processing pipeline.
        It tags the message with metadata to indicate its system origin.
        """
        try:
            team_id = self._team_manager.team_id
            logger.info(f"Team '{team_id}': Dispatching notification for runnable task '{task.task_name}' to assignee '{task.assignee_name}'.")
            
            context_from_parents = []
            if task.dependencies:
                parent_task_deliverables_info = []
                for dep_id in task.dependencies:
                    parent_task = self._task_board._task_map.get(dep_id)
                    if parent_task and parent_task.file_deliverables:
                        deliverables_str = "\n".join(
                            [f"  - File: {d.file_path}, Summary: {d.summary}" for d in parent_task.file_deliverables]
                        )
                        parent_task_deliverables_info.append(
                            f"The parent task '{parent_task.task_name}' produced the following deliverables:\n{deliverables_str}"
                        )
                
                if parent_task_deliverables_info:
                    context_from_parents.append(
                        "Your task is now unblocked. Here is the context from the completed parent task(s):\n" +
                        "\n\n".join(parent_task_deliverables_info)
                    )

            message_parts: List[str] = [f"Your task '{task.task_name}' is now ready to start."]
            if context_from_parents:
                message_parts.extend(context_from_parents)
            
            message_parts.append(f"\nYour task description:\n{task.description}")
            
            content = "\n\n".join(message_parts)
            
            user_message = AgentInputUserMessage(
                content=content,
                metadata={'source': 'system_task_notifier'}
            )
            event = ProcessUserMessageEvent(
                user_message=user_message,
                target_agent_name=task.assignee_name
            )

            await self._team_manager.dispatch_user_message_to_agent(event)
            self._dispatched_task_ids.add(task.task_id)

        except Exception as e:
            logger.error(f"Team '{self._team_manager.team_id}': Failed to dispatch notification for task '{task.task_id}': {e}", exc_info=True)
