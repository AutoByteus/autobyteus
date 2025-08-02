# file: autobyteus/autobyteus/agent_team/shutdown_steps/agent_team_shutdown_orchestrator.py
import logging
from typing import TYPE_CHECKING, List, Optional

from autobyteus.agent_team.shutdown_steps.base_agent_team_shutdown_step import BaseAgentTeamShutdownStep
from autobyteus.agent_team.shutdown_steps.bridge_cleanup_step import BridgeCleanupStep
from autobyteus.agent_team.shutdown_steps.sub_team_shutdown_step import SubTeamShutdownStep
from autobyteus.agent_team.shutdown_steps.agent_team_shutdown_step import AgentTeamShutdownStep

if TYPE_CHECKING:
    from autobyteus.agent_team.context.agent_team_context import AgentTeamContext

logger = logging.getLogger(__name__)

class AgentTeamShutdownOrchestrator:
    """Orchestrates the agent team's shutdown process."""
    def __init__(self, steps: Optional[List[BaseAgentTeamShutdownStep]] = None):
        self.shutdown_steps = steps or [
            BridgeCleanupStep(),
            SubTeamShutdownStep(),
            AgentTeamShutdownStep(),
        ]

    async def run(self, context: 'AgentTeamContext') -> bool:
        team_id = context.team_id
        logger.info(f"Team '{team_id}': Shutdown orchestrator starting.")
        
        all_successful = True
        for step in self.shutdown_steps:
            if not await step.execute(context):
                logger.error(f"Team '{team_id}': Shutdown step {step.__class__.__name__} failed.")
                all_successful = False
        
        logger.info(f"Team '{team_id}': Shutdown orchestration completed.")
        return all_successful
