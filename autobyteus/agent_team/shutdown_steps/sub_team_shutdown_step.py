# file: autobyteus/autobyteus/agent_team/shutdown_steps/sub_team_shutdown_step.py
import asyncio
import logging
from typing import TYPE_CHECKING

from autobyteus.agent_team.shutdown_steps.base_agent_team_shutdown_step import BaseAgentTeamShutdownStep

if TYPE_CHECKING:
    from autobyteus.agent_team.context.agent_team_context import AgentTeamContext

logger = logging.getLogger(__name__)

class SubTeamShutdownStep(BaseAgentTeamShutdownStep):
    """Shutdown step to gracefully stop all running sub-teams."""
    async def execute(self, context: 'AgentTeamContext') -> bool:
        team_id = context.team_id
        logger.info(f"Team '{team_id}': Executing SubTeamShutdownStep.")
        
        team_manager = context.team_manager
        if not team_manager:
            logger.warning(f"Team '{team_id}': No TeamManager found, cannot shut down sub-teams.")
            return True

        all_sub_teams = team_manager.get_all_sub_teams()
        running_sub_teams = [wf for wf in all_sub_teams if wf.is_running]
        
        if not running_sub_teams:
            logger.info(f"Team '{team_id}': No running sub-teams to shut down.")
            return True
        
        logger.info(f"Team '{team_id}': Shutting down {len(running_sub_teams)} running sub-teams.")
        stop_tasks = [team.stop(timeout=20.0) for team in running_sub_teams]
        results = await asyncio.gather(*stop_tasks, return_exceptions=True)
        
        all_successful = True
        for team, result in zip(running_sub_teams, results):
            if isinstance(result, Exception):
                logger.error(f"Team '{team_id}': Error stopping sub-team '{team.name}': {result}", exc_info=result)
                all_successful = False
        
        return all_successful
