# file: autobyteus/autobyteus/agent/workflow/bootstrap_steps/coordinator_and_team_context_initialization_step.py
import logging
from typing import TYPE_CHECKING

from .base_workflow_bootstrap_step import BaseWorkflowBootstrapStep
from ..context.team_context import TeamContext

if TYPE_CHECKING:
    from ..context.workflow_context import WorkflowContext
    from ..phases.workflow_phase_manager import WorkflowPhaseManager
    from ..runtime.workflow_runtime import WorkflowRuntime

logger = logging.getLogger(__name__)

class CoordinatorAndTeamContextInitializationStep(BaseWorkflowBootstrapStep):
    """
    Bootstrap step that initializes the agent team for lazy loading.
    It creates a TeamContext and then uses it to eagerly instantiate the
    coordinator agent, which ensures all necessary dependencies are injected
    correctly from a single source of truth.
    """
    async def execute(self, context: 'WorkflowContext', phase_manager: 'WorkflowPhaseManager') -> bool:
        workflow_id = context.workflow_id
        logger.info(f"Workflow '{workflow_id}': Executing CoordinatorAndTeamContextInitializationStep.")
        
        try:
            runtime_ref: 'WorkflowRuntime' = phase_manager.notifier.runtime_ref
            
            # 1. Prepare for lazy initialization of member agents
            friendly_name_to_node_config_map = {uid: node for node, uid in context.state.member_node_ids.items()}

            # 2. Create a TeamContext to manage the team and lazy creation.
            # The communicator is created inside TeamContext, using the provided callback.
            team_context = TeamContext(
                workflow_id=workflow_id,
                node_configs_by_friendly_name=friendly_name_to_node_config_map,
                submit_event_callback=runtime_ref.submit_event
            )
            
            # 3. Eagerly create the coordinator agent using the TeamContext.
            # This ensures the coordinator gets the same dependency injections as any other agent.
            coordinator_config = context.state.modified_coordinator_config
            coordinator_agent = team_context.get_and_configure_coordinator(coordinator_config)
            
            # 4. Store coordinator in the workflow state
            context.state.coordinator_agent = coordinator_agent
            # The TeamContext now manages the list of all agents, so we just need to add the coordinator here initially.
            # Other agents will be added as they are created.
            context.state.agents = [coordinator_agent]

            logger.info(f"Workflow '{workflow_id}': Coordinator initialized. TeamContext created for lazy agent initialization.")
            return True
        
        except Exception as e:
            logger.error(f"Workflow '{workflow_id}': Failed to initialize agent team: {e}", exc_info=True)
            return False
