# file: autobyteus/autobyteus/agent_team/bootstrap_steps/agent_team_runtime_queue_initialization_step.py
import logging
from typing import TYPE_CHECKING

from autobyteus.agent_team.bootstrap_steps.base_agent_team_bootstrap_step import BaseAgentTeamBootstrapStep
from autobyteus.agent_team.events.agent_team_input_event_queue_manager import AgentTeamInputEventQueueManager

if TYPE_CHECKING:
    from autobyteus.agent_team.context.agent_team_context import AgentTeamContext
    from autobyteus.agent_team.phases.agent_team_phase_manager import AgentTeamPhaseManager

logger = logging.getLogger(__name__)

class AgentTeamRuntimeQueueInitializationStep(BaseAgentTeamBootstrapStep):
    """Bootstrap step for initializing the agent team's runtime event queues."""
    async def execute(self, context: 'AgentTeamContext', phase_manager: 'AgentTeamPhaseManager') -> bool:
        team_id = context.team_id
        logger.info(f"Team '{team_id}': Executing AgentTeamRuntimeQueueInitializationStep.")
        try:
            context.state.input_event_queues = AgentTeamInputEventQueueManager()
            logger.info(f"Team '{team_id}': AgentTeamInputEventQueueManager initialized.")
            return True
        except Exception as e:
            logger.error(f"Team '{team_id}': Critical failure during queue initialization: {e}", exc_info=True)
            return False
