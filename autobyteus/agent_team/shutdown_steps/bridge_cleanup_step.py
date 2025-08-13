# file: autobyteus/autobyteus/agent_team/shutdown_steps/bridge_cleanup_step.py
import logging
from typing import TYPE_CHECKING

from autobyteus.agent_team.shutdown_steps.base_agent_team_shutdown_step import BaseAgentTeamShutdownStep

if TYPE_CHECKING:
    from autobyteus.agent_team.context.agent_team_context import AgentTeamContext

logger = logging.getLogger(__name__)

class BridgeCleanupStep(BaseAgentTeamShutdownStep):
    """Shutdown step to gracefully stop all AgentEventBridge instances via the multiplexer."""
    async def execute(self, context: 'AgentTeamContext') -> bool:
        team_id = context.team_id
        logger.info(f"Team '{team_id}': Executing BridgeCleanupStep.")
        
        multiplexer = context.multiplexer
        if not multiplexer:
            logger.warning(f"Team '{team_id}': No AgentEventMultiplexer found, cannot shut down event bridges.")
            return True

        try:
            await multiplexer.shutdown()
            return True
        except Exception as e:
            logger.error(f"Team '{team_id}': Error shutting down agent event bridges via multiplexer: {e}", exc_info=True)
            return False
