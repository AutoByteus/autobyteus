# file: autobyteus/autobyteus/workflow/shutdown_steps/sub_workflow_shutdown_step.py
import asyncio
import logging
from typing import TYPE_CHECKING

from autobyteus.workflow.shutdown_steps.base_workflow_shutdown_step import BaseWorkflowShutdownStep

if TYPE_CHECKING:
    from autobyteus.workflow.context.workflow_context import WorkflowContext

logger = logging.getLogger(__name__)

class SubWorkflowShutdownStep(BaseWorkflowShutdownStep):
    """Shutdown step to gracefully stop all running sub-workflows."""
    async def execute(self, context: 'WorkflowContext') -> bool:
        workflow_id = context.workflow_id
        logger.info(f"Workflow '{workflow_id}': Executing SubWorkflowShutdownStep.")
        
        team_manager = context.team_manager
        if not team_manager:
            logger.warning(f"Workflow '{workflow_id}': No TeamManager found, cannot shut down sub-workflows.")
            return True

        all_sub_workflows = team_manager.get_all_sub_workflows()
        running_sub_workflows = [wf for wf in all_sub_workflows if wf.is_running]
        
        if not running_sub_workflows:
            logger.info(f"Workflow '{workflow_id}': No running sub-workflows to shut down.")
            return True
        
        logger.info(f"Workflow '{workflow_id}': Shutting down {len(running_sub_workflows)} running sub-workflows.")
        stop_tasks = [wf.stop(timeout=20.0) for wf in running_sub_workflows]
        results = await asyncio.gather(*stop_tasks, return_exceptions=True)
        
        all_successful = True
        for wf, result in zip(running_sub_workflows, results):
            if isinstance(result, Exception):
                logger.error(f"Workflow '{workflow_id}': Error stopping sub-workflow '{wf.name}': {result}", exc_info=result)
                all_successful = False
        
        return all_successful
