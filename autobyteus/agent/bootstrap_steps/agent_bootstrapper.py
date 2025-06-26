# file: autobyteus/autobyteus/agent/bootstrap_steps/agent_bootstrapper.py
import logging
from typing import TYPE_CHECKING, List, Optional

from .base_bootstrap_step import BaseBootstrapStep
from .agent_runtime_queue_initialization_step import AgentRuntimeQueueInitializationStep
from .workspace_context_initialization_step import WorkspaceContextInitializationStep
from .system_prompt_processing_step import SystemPromptProcessingStep
from autobyteus.agent.events import AgentReadyEvent

if TYPE_CHECKING:
    from autobyteus.agent.context import AgentContext
    from autobyteus.agent.phases import AgentPhaseManager

logger = logging.getLogger(__name__)

class AgentBootstrapper:
    """
    Orchestrates the agent's bootstrapping process by executing a sequence of
    self-contained bootstrap steps.
    """
    def __init__(self, steps: Optional[List[BaseBootstrapStep]] = None):
        """
        Initializes the AgentBootstrapper.

        Args:
            steps: An optional list of bootstrap steps to execute. If not provided,
                   a default sequence will be used.
        """
        if steps is None:
            self.bootstrap_steps: List[BaseBootstrapStep] = [
                AgentRuntimeQueueInitializationStep(),
                WorkspaceContextInitializationStep(),
                SystemPromptProcessingStep(),
            ]
            logger.debug("AgentBootstrapper initialized with default steps.")
        else:
            self.bootstrap_steps = steps
            logger.debug(f"AgentBootstrapper initialized with {len(steps)} custom steps.")

    async def run(self, context: 'AgentContext', phase_manager: 'AgentPhaseManager') -> bool:
        """
        Executes the configured sequence of bootstrap steps.

        Args:
            context: The agent's context.
            phase_manager: The agent's phase manager.

        Returns:
            True if all steps completed successfully, False otherwise.
        """
        agent_id = context.agent_id
        
        # Set the agent phase to BOOTSTRAPPING and wait for any associated hooks.
        await phase_manager.notify_bootstrapping_started()
        logger.info(f"Agent '{agent_id}': AgentBootstrapper starting execution. Phase set to BOOTSTRAPPING.")

        for step_index, step_instance in enumerate(self.bootstrap_steps):
            step_name = step_instance.__class__.__name__
            logger.debug(f"Agent '{agent_id}': Executing bootstrap step {step_index + 1}/{len(self.bootstrap_steps)}: {step_name}")
            
            success = await step_instance.execute(context, phase_manager)
            
            if not success:
                error_message = f"Bootstrap step {step_name} failed."
                logger.error(f"Agent '{agent_id}': {error_message} Halting bootstrap process.")
                # The step itself is responsible for detailed error logging.
                # We are responsible for notifying the phase manager to set the agent to an error state.
                await phase_manager.notify_error_occurred(
                    error_message=f"Critical bootstrap failure at {step_name}",
                    error_details=f"Agent '{agent_id}' failed during bootstrap step '{step_name}'. Check logs for details."
                )
                return False

        logger.info(f"Agent '{agent_id}': All bootstrap steps completed successfully. Enqueuing AgentReadyEvent.")
        # After successful bootstrapping, enqueue the ready event.
        if context.state.input_event_queues:
            await context.state.input_event_queues.enqueue_internal_system_event(AgentReadyEvent())
        else: # pragma: no cover
            # Should not happen if AgentRuntimeQueueInitializationStep is present and successful
            logger.critical(f"Agent '{agent_id}': Bootstrap succeeded but input queues are not available to enqueue AgentReadyEvent.")
            await phase_manager.notify_error_occurred(
                error_message="Input queues unavailable after bootstrap",
                error_details=f"Agent '{agent_id}' bootstrap process seemed to succeed, but input event queues are missing."
            )
            return False
            
        return True
