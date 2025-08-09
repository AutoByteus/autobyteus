# file: autobyteus/autobyteus/agent_team/bootstrap_steps/team_context_initialization_step.py
import logging
from typing import TYPE_CHECKING

from autobyteus.agent_team.bootstrap_steps.base_agent_team_bootstrap_step import BaseAgentTeamBootstrapStep
from autobyteus.task_management import TaskBoard

if TYPE_CHECKING:
    from autobyteus.agent_team.context.agent_team_context import AgentTeamContext
    from autobyteus.agent_team.phases.agent_team_phase_manager import AgentTeamPhaseManager

logger = logging.getLogger(__name__)

class TeamContextInitializationStep(BaseAgentTeamBootstrapStep):
    """
    Bootstrap step to initialize shared team context components, such as the
    TaskBoard and the artifact registry.
    """
    async def execute(self, context: 'AgentTeamContext', phase_manager: 'AgentTeamPhaseManager') -> bool:
        team_id = context.team_id
        logger.info(f"Team '{team_id}': Executing TeamContextInitializationStep.")
        try:
            # The artifact_registry is already initialized as a dict in AgentTeamRuntimeState.
            # Here, we initialize the TaskBoard.
            if context.state.task_board is None:
                context.state.task_board = TaskBoard(team_id=team_id)
                logger.info(f"Team '{team_id}': TaskBoard initialized and attached to team state.")
            else:
                logger.warning(f"Team '{team_id}': TaskBoard already exists. Skipping initialization.")

            return True
        except Exception as e:
            logger.error(f"Team '{team_id}': Critical failure during team context initialization: {e}", exc_info=True)
            return False
