# file: autobyteus/autobyteus/agent_team/bootstrap_steps/coordinator_initialization_step.py
import logging
from typing import TYPE_CHECKING

from autobyteus.agent_team.bootstrap_steps.base_agent_team_bootstrap_step import BaseAgentTeamBootstrapStep

if TYPE_CHECKING:
    from autobyteus.agent_team.context.agent_team_context import AgentTeamContext
    from autobyteus.agent_team.phases.agent_team_phase_manager import AgentTeamPhaseManager

logger = logging.getLogger(__name__)

class CoordinatorInitializationStep(BaseAgentTeamBootstrapStep):
    """
    Bootstrap step that eagerly instantiates and starts the coordinator agent
    using the TeamManager. This ensures the coordinator is ready before the
    agent team becomes idle.
    """
    async def execute(self, context: 'AgentTeamContext', phase_manager: 'AgentTeamPhaseManager') -> bool:
        team_id = context.team_id
        logger.info(f"Team '{team_id}': Executing CoordinatorInitializationStep.")
        
        try:
            team_manager = context.team_manager
            if not team_manager:
                raise RuntimeError("TeamManager not found in team context. It should be created by the factory.")

            coordinator_name = context.config.coordinator_node.name

            # This call now ensures the coordinator agent is fully created and ready.
            coordinator = await team_manager.ensure_coordinator_is_ready(coordinator_name)
            
            if not coordinator:
                raise RuntimeError(f"TeamManager failed to return a ready coordinator agent for '{coordinator_name}'.")

            logger.info(f"Team '{team_id}': Coordinator '{coordinator_name}' initialized and started via TeamManager.")
            return True
        
        except Exception as e:
            logger.error(f"Team '{team_id}': Failed to initialize coordinator agent: {e}", exc_info=True)
            return False
