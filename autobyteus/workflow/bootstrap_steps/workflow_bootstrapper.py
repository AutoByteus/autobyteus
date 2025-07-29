# file: autobyteus/autobyteus/workflow/bootstrap_steps/workflow_bootstrapper.py
import logging
from typing import TYPE_CHECKING, List, Optional

from autobyteus.workflow.bootstrap_steps.base_workflow_bootstrap_step import BaseWorkflowBootstrapStep
from autobyteus.workflow.bootstrap_steps.workflow_runtime_queue_initialization_step import WorkflowRuntimeQueueInitializationStep
from autobyteus.workflow.bootstrap_steps.coordinator_prompt_preparation_step import CoordinatorPromptPreparationStep
from autobyteus.workflow.bootstrap_steps.agent_tool_injection_step import AgentToolInjectionStep
from autobyteus.workflow.bootstrap_steps.coordinator_initialization_step import CoordinatorInitializationStep
from autobyteus.workflow.events.workflow_events import WorkflowReadyEvent

if TYPE_CHECKING:
    from autobyteus.workflow.context.workflow_context import WorkflowContext
    from autobyteus.workflow.phases.workflow_phase_manager import WorkflowPhaseManager

logger = logging.getLogger(__name__)

class WorkflowBootstrapper:
    """Orchestrates the workflow's bootstrapping process."""
    def __init__(self, steps: Optional[List[BaseWorkflowBootstrapStep]] = None):
        self.bootstrap_steps = steps or [
            WorkflowRuntimeQueueInitializationStep(),
            CoordinatorPromptPreparationStep(),
            AgentToolInjectionStep(),
            CoordinatorInitializationStep(),
        ]

    async def run(self, context: 'WorkflowContext', phase_manager: 'WorkflowPhaseManager') -> bool:
        workflow_id = context.workflow_id
        await phase_manager.notify_bootstrapping_started()
        logger.info(f"Workflow '{workflow_id}': Bootstrapper starting.")

        for step in self.bootstrap_steps:
            step_name = step.__class__.__name__
            logger.debug(f"Workflow '{workflow_id}': Executing bootstrap step: {step_name}")
            if not await step.execute(context, phase_manager):
                error_message = f"Bootstrap step {step_name} failed."
                logger.error(f"Workflow '{workflow_id}': {error_message}")
                await phase_manager.notify_error_occurred(error_message, f"Failed during bootstrap step '{step_name}'.")
                return False
        
        logger.info(f"Workflow '{workflow_id}': All bootstrap steps completed successfully.")
        if context.state.input_event_queues:
            await context.state.input_event_queues.enqueue_internal_system_event(WorkflowReadyEvent())
        else:
            logger.critical(f"Workflow '{workflow_id}': Bootstrap succeeded but queues not available.")
            await phase_manager.notify_error_occurred("Queues unavailable after bootstrap.", "")
            return False
            
        return True
