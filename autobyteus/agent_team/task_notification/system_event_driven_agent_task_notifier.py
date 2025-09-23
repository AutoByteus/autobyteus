# file: autobyteus/autobyteus/agent_team/task_notification/system_event_driven_agent_task_notifier.py
import logging
from typing import Union, TYPE_CHECKING

from autobyteus.events.event_types import EventType
from autobyteus.task_management.events import TasksAddedEvent, TaskStatusUpdatedEvent
from autobyteus.task_management.base_task_board import TaskStatus

# Import the new, separated components
from .activation_policy import ActivationPolicy
from .task_activator import TaskActivator

if TYPE_CHECKING:
    from autobyteus.task_management.base_task_board import BaseTaskBoard
    from autobyteus.agent_team.context.team_manager import TeamManager

logger = logging.getLogger(__name__)

class SystemEventDrivenAgentTaskNotifier:
    """
    An internal component that monitors a TaskBoard and orchestrates agent
    activation based on task runnability.

    This class acts as a conductor, delegating the logic for *when* to activate
    to an ActivationPolicy and the action of *how* to activate to a TaskActivator.
    """
    def __init__(self, task_board: 'BaseTaskBoard', team_manager: 'TeamManager'):
        """
        Initializes the SystemEventDrivenAgentTaskNotifier.

        Args:
            task_board: The team's shared task board instance.
            team_manager: The team's manager for activating agents.
        """
        if not task_board or not team_manager:
            raise ValueError("TaskBoard and TeamManager are required for the notifier.")
            
        self._task_board = task_board
        self._team_manager = team_manager
        
        # Instantiate the components that hold the actual logic and action
        self._policy = ActivationPolicy(team_id=self._team_manager.team_id)
        self._activator = TaskActivator(team_manager=self._team_manager)

        logger.info(f"SystemEventDrivenAgentTaskNotifier orchestrator initialized for team '{self._team_manager.team_id}'.")

    def start_monitoring(self):
        """
        Subscribes to task board events to begin monitoring for runnable tasks.
        """
        self._task_board.subscribe(EventType.TASK_BOARD_TASKS_ADDED, self._handle_tasks_changed)
        self._task_board.subscribe(EventType.TASK_BOARD_STATUS_UPDATED, self._handle_tasks_changed)
        logger.info(f"Team '{self._team_manager.team_id}': Task notifier orchestrator is now monitoring TaskBoard events.")
    
    async def _handle_tasks_changed(self, payload: Union[TasksAddedEvent, TaskStatusUpdatedEvent], **kwargs):
        """
        Orchestrates the agent activation workflow upon any change to the task board.
        """
        team_id = self._team_manager.team_id
        logger.info(f"Team '{team_id}': Task board changed ({type(payload).__name__}). Orchestrating activation check.")

        # If a new batch of tasks was added, it's a new "wave" of work.
        # We must reset the policy's memory of who has been activated.
        if isinstance(payload, TasksAddedEvent):
            logger.info(f"Team '{team_id}': New tasks added. Resetting activation policy.")
            self._policy.reset()

        # 1. DATA FETCHING: Get the current state of runnable tasks from the board.
        runnable_tasks = self._task_board.get_next_runnable_tasks()
        
        if not runnable_tasks:
            logger.debug(f"Team '{team_id}': No runnable tasks found after change. No action needed.")
            return

        # 2. POLICY DECISION: Ask the policy to decide which agents to activate.
        # The policy contains all the complex state and logic.
        agents_to_activate = self._policy.determine_activations(runnable_tasks)

        if not agents_to_activate:
            logger.info(f"Team '{team_id}': Runnable tasks exist, but policy determined no new agents need activation.")
            return

        # 3. ACTION EXECUTION: Tell the activator to perform the activations.
        for agent_name in agents_to_activate:
            # First, update the status for all of that agent's runnable tasks to QUEUED.
            # This is a state change action, which the orchestrator is responsible for.
            agent_runnable_tasks = [t for t in runnable_tasks if t.assignee_name == agent_name]
            for task in agent_runnable_tasks:
                # We only need to queue tasks that are NOT_STARTED.
                if self._task_board.task_statuses.get(task.task_id) == TaskStatus.NOT_STARTED:
                    self._task_board.update_task_status(
                        task_id=task.task_id,
                        status=TaskStatus.QUEUED,
                        agent_name="SystemTaskNotifier"
                    )
            
            # Now, trigger the single activation notification.
            await self._activator.activate_agent(agent_name)
