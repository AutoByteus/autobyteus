# file: autobyteus/autobyteus/workflow/bootstrap_steps/workflow_runtime_queue_initialization_step.py
import logging
from typing import TYPE_CHECKING

from autobyteus.workflow.bootstrap_steps.base_workflow_bootstrap_step import BaseWorkflowBootstrapStep
from autobyteus.workflow.events.workflow_input_event_queue_manager import WorkflowInputEventQueueManager

if TYPE_CHECKING:
    from autobyteus.workflow.context.workflow_context import WorkflowContext
    from autobyteus.workflow.phases.workflow_phase_manager import WorkflowPhaseManager

logger = logging.getLogger(__name__)

class WorkflowRuntimeQueueInitializationStep(BaseWorkflowBootstrapStep):
    """Bootstrap step for initializing the workflow's runtime event queues."""
    async def execute(self, context: 'WorkflowContext', phase_manager: 'WorkflowPhaseManager') -> bool:
        workflow_id = context.workflow_id
        logger.info(f"Workflow '{workflow_id}': Executing WorkflowRuntimeQueueInitializationStep.")
        try:
            context.state.input_event_queues = WorkflowInputEventQueueManager()
            logger.info(f"Workflow '{workflow_id}': WorkflowInputEventQueueManager initialized.")
            return True
        except Exception as e:
            logger.error(f"Workflow '{workflow_id}': Critical failure during queue initialization: {e}", exc_info=True)
            return False
