# file: autobyteus/autobyteus/agent_team/bootstrap_steps/task_notifier_initialization_step.py
import logging
from typing import TYPE_CHECKING

from autobyteus.agent_team.bootstrap_steps.base_agent_team_bootstrap_step import BaseAgentTeamBootstrapStep
from autobyteus.agent_team.task_notification.task_notification_mode import TaskNotificationMode
from autobyteus.agent_team.task_notification.system_event_driven_agent_task_notifier import SystemEventDrivenAgentTaskNotifier

if TYPE_CHECKING:
    from autobyteus.agent_team.context.agent_team_context import AgentTeamContext
    from autobyteus.agent_team.phases.agent_team_phase_manager import AgentTeamPhaseManager

logger = logging.getLogger(__name__)

class TaskNotifierInitializationStep(BaseAgentTeamBootstrapStep):
    """
    Bootstrap step to initialize the SystemEventDrivenAgentTaskNotifier if the
    team is configured for event-driven notifications.
    """
    async def execute(self, context: 'AgentTeamContext', phase_manager: 'AgentTeamPhaseManager') -> bool:
        team_id = context.team_id
        logger.info(f"Team '{team_id}': Executing TaskNotifierInitializationStep.")
        
        if context.config.task_notification_mode != TaskNotificationMode.SYSTEM_EVENT_DRIVEN:
            logger.info(f"Team '{team_id}': Task notification mode is '{context.config.task_notification_mode.value}'. Skipping event-driven notifier setup.")
            return True

        logger.info(f"Team '{team_id}': Mode is SYSTEM_EVENT_DRIVEN. Initializing and activating task notifier.")
        try:
            task_board = context.state.task_board
            if not task_board:
                logger.error(f"Team '{team_id}': TaskBoard not found. Cannot initialize task notifier. This step should run after TeamContextInitializationStep.")
                return False

            team_manager = context.team_manager
            if not team_manager:
                logger.error(f"Team '{team_id}': TeamManager not found. Cannot initialize task notifier.")
                return False

            notifier = SystemEventDrivenAgentTaskNotifier(
                task_board=task_board, 
                team_manager=team_manager
            )
            notifier.start_monitoring()
            
            context.state.task_notifier = notifier
            logger.info(f"Team '{team_id}': SystemEventDrivenAgentTaskNotifier initialized and monitoring started.")
            return True
        except Exception as e:
            logger.error(f"Team '{team_id}': Critical failure during task notifier initialization: {e}", exc_info=True)
            return False
