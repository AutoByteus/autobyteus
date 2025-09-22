import asyncio
import logging
from typing import Set, Any, TYPE_CHECKING, List, Union, Dict
from collections import defaultdict

from autobyteus.events.event_types import EventType
from autobyteus.agent_team.events import ProcessUserMessageEvent
from autobyteus.agent.message import AgentInputUserMessage
from autobyteus.task_management.events import TasksAddedEvent, TaskStatusUpdatedEvent
from autobyteus.task_management.base_task_board import TaskStatus
from autobyteus.task_management.task import Task

if TYPE_CHECKING:
    from autobyteus.task_management.base_task_board import BaseTaskBoard
    from autobyteus.agent_team.context.team_manager import TeamManager
    from autobyteus.agent.agent import Agent

logger = logging.getLogger(__name__)

class SystemEventDrivenAgentTaskNotifier:
    """
    An internal component that monitors a TaskBoard. When it finds runnable tasks,
    it updates their status to QUEUED and sends a single, generic notification
    to the assigned agent to trigger their work cycle.
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
        # This set tracks which agents have been notified about new work in the current cycle.
        self._notified_agents: Set[str] = set()
        logger.info(f"SystemEventDrivenAgentTaskNotifier initialized for team '{self._team_manager.team_id}'.")

    def start_monitoring(self):
        """
        Subscribes to task board events to begin monitoring for runnable tasks.
        """
        self._task_board.subscribe(EventType.TASK_BOARD_TASKS_ADDED, self._handle_tasks_changed)
        self._task_board.subscribe(EventType.TASK_BOARD_STATUS_UPDATED, self._handle_tasks_changed)
        logger.info(f"Team '{self._team_manager.team_id}': Task notifier is now monitoring TaskBoard events.")
    
    async def _handle_tasks_changed(self, payload: Union[TasksAddedEvent, TaskStatusUpdatedEvent], **kwargs):
        """
        Generic handler for any event that might change task runnability.
        """
        logger.info(f"Team '{self._team_manager.team_id}': Task board changed. Scanning for new runnable tasks.")
        self._notified_agents.clear() # Reset for the new scan cycle
        await self._scan_and_notify_runnable_tasks()

    async def _scan_and_notify_runnable_tasks(self):
        """
        Scans the task board for runnable (NOT_STARTED) tasks, updates their
        status to QUEUED, and sends a single notification per affected agent.
        """
        runnable_tasks = self._task_board.get_next_runnable_tasks()

        if not runnable_tasks:
            return

        # Group tasks by agent to send a single notification
        tasks_by_agent: Dict[str, List[Task]] = defaultdict(list)
        for task in runnable_tasks:
            # Only consider tasks that are not yet queued or processed.
            if self._task_board.task_statuses.get(task.task_id) == TaskStatus.NOT_STARTED:
                tasks_by_agent[task.assignee_name].append(task)
        
        for agent_name, tasks_to_queue in tasks_by_agent.items():
            if not tasks_to_queue:
                continue

            # 1. Update status on the global task board to QUEUED
            for task in tasks_to_queue:
                self._task_board.update_task_status(
                    task_id=task.task_id,
                    status=TaskStatus.QUEUED,
                    agent_name="SystemTaskNotifier"
                )
            
            # 2. Send the single, generic notification to trigger the agent's work cycle
            if agent_name not in self._notified_agents:
                await self._notify_agent(agent_name, len(tasks_to_queue))
                self._notified_agents.add(agent_name)

    async def _notify_agent(self, agent_name: str, task_count: int):
        """Sends a single, generic trigger message to an agent."""
        team_id = self._team_manager.team_id
        try:
            logger.info(f"Team '{team_id}': Notifying agent '{agent_name}' about {task_count} new task(s) in their queue.")
            
            # This ensures the agent is started and ready to receive the message.
            await self._team_manager.ensure_node_is_ready(agent_name)

            notification_message = AgentInputUserMessage(
                content="You have new tasks in your queue. Please review your task list using your tools and begin your work.",
                metadata={'source': 'system_task_notifier'}
            )
            event = ProcessUserMessageEvent(
                user_message=notification_message,
                target_agent_name=agent_name
            )
            await self._team_manager.dispatch_user_message_to_agent(event)
            
            logger.info(f"Team '{team_id}': Successfully sent task notification to '{agent_name}'.")

        except Exception as e:
            logger.error(f"Team '{team_id}': Failed to notify agent '{agent_name}': {e}", exc_info=True)
