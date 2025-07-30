# file: autobyteus/autobyteus/workflow/shutdown_steps/bridge_cleanup_step.py
import logging
from typing import TYPE_CHECKING

from autobyteus.workflow.shutdown_steps.base_workflow_shutdown_step import BaseWorkflowShutdownStep

if TYPE_CHECKING:
    from autobyteus.workflow.context.workflow_context import WorkflowContext

logger = logging.getLogger(__name__)

class BridgeCleanupStep(BaseWorkflowShutdownStep):
    """Shutdown step to gracefully stop all AgentEventBridge instances via the multiplexer."""
    async def execute(self, context: 'WorkflowContext') -> bool:
        workflow_id = context.workflow_id
        logger.info(f"Workflow '{workflow_id}': Executing BridgeCleanupStep.")
        
        multiplexer = context.multiplexer
        if not multiplexer:
            logger.warning(f"Workflow '{workflow_id}': No AgentEventMultiplexer found, cannot shut down event bridges.")
            return True

        try:
            await multiplexer.shutdown()
            return True
        except Exception as e:
            logger.error(f"Workflow '{workflow_id}': Error shutting down agent event bridges via multiplexer: {e}", exc_info=True)
            return False
