# file: autobyteus/autobyteus/workflow/shutdown_steps/agent_team_shutdown_step.py
import asyncio
import logging
from typing import TYPE_CHECKING

from autobyteus.workflow.shutdown_steps.base_workflow_shutdown_step import BaseWorkflowShutdownStep

if TYPE_CHECKING:
    from autobyteus.workflow.context.workflow_context import WorkflowContext

logger = logging.getLogger(__name__)

class AgentTeamShutdownStep(BaseWorkflowShutdownStep):
    """Shutdown step to gracefully stop all running agents in the workflow."""
    async def execute(self, context: 'WorkflowContext') -> bool:
        workflow_id = context.workflow_id
        logger.info(f"Workflow '{workflow_id}': Executing AgentTeamShutdownStep.")
        
        team_manager = context.team_manager
        if not team_manager:
            logger.warning(f"Workflow '{workflow_id}': No TeamManager found, cannot shut down agents.")
            return True

        # Get the list of all created agents from the single source of truth.
        all_agents = team_manager.get_all_agents()
        running_agents = [agent for agent in all_agents if agent.is_running]
        
        if not running_agents:
            logger.info(f"Workflow '{workflow_id}': No running agents to shut down.")
            return True
        
        logger.info(f"Workflow '{workflow_id}': Shutting down {len(running_agents)} running agents.")
        stop_tasks = [agent.stop(timeout=10.0) for agent in running_agents]
        results = await asyncio.gather(*stop_tasks, return_exceptions=True)
        
        all_successful = True
        for agent, result in zip(running_agents, results):
            if isinstance(result, Exception):
                logger.error(f"Workflow '{workflow_id}': Error stopping agent '{agent.agent_id}': {result}", exc_info=result)
                all_successful = False
        
        return all_successful
