# file: autobyteus/autobyteus/workflow/bootstrap_steps/coordinator_initialization_step.py
import logging
from typing import TYPE_CHECKING

from autobyteus.workflow.bootstrap_steps.base_workflow_bootstrap_step import BaseWorkflowBootstrapStep

if TYPE_CHECKING:
    from autobyteus.workflow.context.workflow_context import WorkflowContext
    from autobyteus.workflow.phases.workflow_phase_manager import WorkflowPhaseManager

logger = logging.getLogger(__name__)

class CoordinatorInitializationStep(BaseWorkflowBootstrapStep):
    """
    Bootstrap step that eagerly instantiates and starts the coordinator agent
    using the TeamManager. This ensures the coordinator is ready before the
    workflow becomes idle.
    """
    async def execute(self, context: 'WorkflowContext', phase_manager: 'WorkflowPhaseManager') -> bool:
        workflow_id = context.workflow_id
        logger.info(f"Workflow '{workflow_id}': Executing CoordinatorInitializationStep.")
        
        try:
            team_manager = context.team_manager
            if not team_manager:
                raise RuntimeError("TeamManager not found in workflow context. It should be created by the factory.")

            coordinator_name = context.config.coordinator_node.name

            # This call now ensures the coordinator agent is fully created and ready.
            coordinator = await team_manager.ensure_coordinator_is_ready(coordinator_name)
            
            if not coordinator:
                raise RuntimeError(f"TeamManager failed to return a ready coordinator agent for '{coordinator_name}'.")

            logger.info(f"Workflow '{workflow_id}': Coordinator '{coordinator_name}' initialized and started via TeamManager.")
            return True
        
        except Exception as e:
            logger.error(f"Workflow '{workflow_id}': Failed to initialize coordinator agent: {e}", exc_info=True)
            return False
