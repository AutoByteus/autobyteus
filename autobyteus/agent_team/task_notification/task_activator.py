# file: autobyteus/autobyteus/agent_team/task_notification/task_activator.py
"""
Defines the component responsible for the action of activating an agent.
"""
import logging
from typing import TYPE_CHECKING

from autobyteus.agent.message import AgentInputUserMessage
from autobyteus.agent_team.events import ProcessUserMessageEvent
from autobyteus.agent.sender_type import SenderType, TASK_NOTIFIER_SENDER_ID

if TYPE_CHECKING:
    from autobyteus.agent_team.context.team_manager import TeamManager

logger = logging.getLogger(__name__)

class TaskActivator:
    """
    A component with the single responsibility of activating an agent.

    Activation involves ensuring the agent is running and sending it a
    standardized "start work" message.
    """
    def __init__(self, team_manager: 'TeamManager'):
        """
        Initializes the TaskActivator.

        Args:
            team_manager: The team's manager, used to start agents and dispatch messages.
        """
        if not team_manager:
            raise ValueError("TaskActivator requires a valid TeamManager instance.")
        self._team_manager = team_manager
        logger.debug(f"TaskActivator initialized for team '{self._team_manager.team_id}'.")

    async def activate_agent(self, agent_name: str):
        """
        Activates a specific agent by ensuring it is ready and sending it a
        generic "start work" notification.

        Args:
            agent_name: The unique name of the agent to activate.
        """
        team_id = self._team_manager.team_id
        try:
            logger.info(f"Team '{team_id}': TaskActivator is activating agent '{agent_name}'.")
            
            # This ensures the agent is started and ready to receive the message.
            await self._team_manager.ensure_node_is_ready(agent_name)

            notification_message = AgentInputUserMessage(
                content="You have new tasks in your queue. Please review your task list using your tools and begin your work.",
                sender_type=SenderType.SYSTEM,
                metadata={'sender_id': TASK_NOTIFIER_SENDER_ID}
            )
            event = ProcessUserMessageEvent(
                user_message=notification_message,
                target_agent_name=agent_name
            )
            await self._team_manager.dispatch_user_message_to_agent(event)
            
            logger.info(f"Team '{team_id}': Successfully sent activation notification to '{agent_name}'.")

        except Exception as e:
            # FIXED: Removed "TaskActivator" from the log message to align with the unit test assertion.
            logger.error(f"Team '{team_id}': Failed to activate agent '{agent_name}': {e}", exc_info=True)
