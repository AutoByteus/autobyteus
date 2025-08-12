# file: autobyteus/autobyteus/agent_team/task_notification/system_event_driven_agent_task_notifier.py
import asyncio
import logging
from typing import Set, Any, TYPE_CHECKING

from autobyteus.events.event_types import EventType
from autobyteus.agent_team.events import InterAgentMessageRequestEvent
from autobyteus.agent.message import InterAgentMessageType
from autobyteus.task_management.events import TaskPlanPublishedEvent

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
        self._task_board.subscribe(
            EventType.TASK_BOARD_PLAN_PUBLISHED,
            self._handle_task_board_update
        )
        self._task_board.subscribe(
            EventType.TASK_BOARD_STATUS_UPDATED,
            self._handle_task_board_update
        )
        logger.info(f"Team '{self._team_manager.team_id}': Task notifier is now monitoring TaskBoard events.")

    async def _handle_task_board_update(self, payload: Any, **kwargs):
        """
        Asynchronous event handler triggered by the task board. It checks for
        newly runnable tasks and dispatches notifications.
        """
        if isinstance(payload, TaskPlanPublishedEvent):
            logger.info(f"Team '{self._team_manager.team_id}': New task plan detected. Resetting dispatched tasks.")
            self._dispatched_task_ids.clear()
        
        await self._notify_agents_for_runnable_tasks()

    async def _notify_agents_for_runnable_tasks(self):
        """
        Queries the task board for runnable tasks and sends a notification event
        for each new runnable task. It uses an internal set to prevent duplicate
        notifications.
        """
        try:
            runnable_tasks = self._task_board.get_next_runnable_tasks()
            if not runnable_tasks:
                return

            team_id = self._team_manager.team_id
            logger.debug(f"Team '{team_id}': Found {len(runnable_tasks)} runnable tasks. Checking for new notifications to send.")

            for task in runnable_tasks:
                if task.task_id in self._dispatched_task_ids:
                    continue

                logger.info(f"Team '{team_id}': Found new runnable task '{task.task_name}' for assignee '{task.assignee_name}'. Dispatching notification.")
                
                content = (
                    f"A new task has been assigned to you and is ready to start.\n\n"
                    f"Task Name: {task.task_name}\n"
                    f"Description: {task.description}"
                )
                
                event = InterAgentMessageRequestEvent(
                    sender_agent_id="system.task_notifier",
                    recipient_name=task.assignee_name,
                    content=content,
                    message_type=InterAgentMessageType.TASK_ASSIGNMENT.value
                )

                await self._team_manager.dispatch_inter_agent_message_request(event)
                self._dispatched_task_ids.add(task.task_id)

        except Exception as e:
            logger.error(f"Team '{self._team_manager.team_id}': Error in task notification logic: {e}", exc_info=True)
