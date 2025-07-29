# file: autobyteus/autobyteus/agent/workflow/shutdown_steps/workflow_shutdown_orchestrator.py
import logging
from typing import TYPE_CHECKING, List, Optional

from .base_workflow_shutdown_step import BaseWorkflowShutdownStep
from .agent_team_shutdown_step import AgentTeamShutdownStep

if TYPE_CHECKING:
    from ..workflow_context import WorkflowContext

logger = logging.getLogger(__name__)

class WorkflowShutdownOrchestrator:
    """Orchestrates the workflow's shutdown process."""
    def __init__(self, steps: Optional[List[BaseWorkflowShutdownStep]] = None):
        self.shutdown_steps = steps or [
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
