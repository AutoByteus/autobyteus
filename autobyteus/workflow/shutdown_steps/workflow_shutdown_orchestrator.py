# file: autobyteus/autobyteus/workflow/shutdown_steps/workflow_shutdown_orchestrator.py
import logging
from typing import TYPE_CHECKING, List, Optional

from autobyteus.workflow.shutdown_steps.base_workflow_shutdown_step import BaseWorkflowShutdownStep
from autobyteus.workflow.shutdown_steps.bridge_cleanup_step import BridgeCleanupStep
from autobyteus.workflow.shutdown_steps.sub_workflow_shutdown_step import SubWorkflowShutdownStep
from autobyteus.workflow.shutdown_steps.agent_team_shutdown_step import AgentTeamShutdownStep

if TYPE_CHECKING:
    from autobyteus.workflow.context.workflow_context import WorkflowContext

logger = logging.getLogger(__name__)

class WorkflowShutdownOrchestrator:
    """Orchestrates the workflow's shutdown process."""
    def __init__(self, steps: Optional[List[BaseWorkflowShutdownStep]] = None):
        self.shutdown_steps = steps or [
            BridgeCleanupStep(),
            SubWorkflowShutdownStep(),
            AgentTeamShutdownStep(),
        ]

    async def run(self, context: 'WorkflowContext') -> bool:
        workflow_id = context.workflow_id
        logger.info(f"Workflow '{workflow_id}': Shutdown orchestrator starting.")
        
        all_successful = True
        for step in self.shutdown_steps:
            if not await step.execute(context):
                logger.error(f"Workflow '{workflow_id}': Shutdown step {step.__class__.__name__} failed.")
                all_successful = False
        
        logger.info(f"Workflow '{workflow_id}': Shutdown orchestration completed.")
        return all_successful
