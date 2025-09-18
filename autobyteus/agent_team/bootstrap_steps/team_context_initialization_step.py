# file: autobyteus/autobyteus/agent_team/bootstrap_steps/team_context_initialization_step.py
import logging
from typing import TYPE_CHECKING

from autobyteus.agent_team.bootstrap_steps.base_agent_team_bootstrap_step import BaseAgentTeamBootstrapStep
from autobyteus.task_management import TaskBoard
from autobyteus.events.event_types import EventType

if TYPE_CHECKING:
    from autobyteus.agent_team.context.agent_team_context import AgentTeamContext
    from autobyteus.agent_team.phases.agent_team_phase_manager import AgentTeamPhaseManager

logger = logging.getLogger(__name__)

class TeamContextInitializationStep(BaseAgentTeamBootstrapStep):
    """
    Bootstrap step to initialize shared team context components, such as the
    TaskBoard, and bridges its events to the team's notifier.
    """
    async def execute(self, context: 'AgentTeamContext', phase_manager: 'AgentTeamPhaseManager') -> bool:
        team_id = context.team_id
        logger.info(f"Team '{team_id}': Executing TeamContextInitializationStep.")
        try:
            if context.state.task_board is None:
                task_board = TaskBoard(team_id=team_id)
                context.state.task_board = task_board
                logger.info(f"Team '{team_id}': TaskBoard initialized and attached to team state.")

                notifier = phase_manager.notifier
                if notifier:
                    # The notifier, a long-lived component, subscribes to events
                    # from the task_board, another long-lived component.
                    notifier.subscribe_from(sender=task_board, event=EventType.TASK_BOARD_TASKS_ADDED, listener=notifier.handle_and_publish_task_board_event)
                    notifier.subscribe_from(sender=task_board, event=EventType.TASK_BOARD_STATUS_UPDATED, listener=notifier.handle_and_publish_task_board_event)
                    logger.info(f"Team '{team_id}': Successfully bridged TaskBoard events to the team notifier.")
                else:
                    logger.warning(f"Team '{team_id}': Notifier not found in PhaseManager. Cannot bridge TaskBoard events.")

            else:
                logger.warning(f"Team '{team_id}': TaskBoard already exists. Skipping initialization.")

            return True
        except Exception as e:
            logger.error(f"Team '{team_id}': Critical failure during team context initialization: {e}", exc_info=True)
            return False
