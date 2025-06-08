# file: autobyteus/autobyteus/agent/handlers/bootstrap_agent_event_handler.py
import logging
from typing import TYPE_CHECKING, List

from autobyteus.agent.handlers.base_event_handler import AgentEventHandler
from autobyteus.agent.events import BootstrapAgentEvent, AgentReadyEvent, AgentErrorEvent 

# Import bootstrap steps
from autobyteus.agent.bootstrap_steps import (
    BaseBootstrapStep,
    AgentRuntimeQueueInitializationStep, # UPDATED
    ToolInitializationStep,
    SystemPromptProcessingStep,
    LLMConfigFinalizationStep,
    LLMInstanceCreationStep
)

if TYPE_CHECKING:
    from autobyteus.agent.context import AgentContext
    from autobyteus.tools.registry import ToolRegistry
    from autobyteus.agent.system_prompt_processor import SystemPromptProcessorRegistry
    from autobyteus.llm.llm_factory import LLMFactory
    from autobyteus.agent.context.agent_phase_manager import AgentPhaseManager


logger = logging.getLogger(__name__)

class BootstrapAgentEventHandler(AgentEventHandler):
    """
    Handles the BootstrapAgentEvent by orchestrating a sequence of individual
    bootstrap step classes. Each step is responsible for a part of the agent
    initialization, including phase notifications and error reporting.
    Enqueues AgentReadyEvent on successful completion of all steps.
    If a step fails, this handler will ensure an AgentErrorEvent is enqueued
    if the failing step couldn't do it itself (e.g., if queues aren't up).
    """

    def __init__(self,
                 tool_registry: 'ToolRegistry',
                 system_prompt_processor_registry: 'SystemPromptProcessorRegistry',
                 llm_factory: 'LLMFactory'):
        
        self.tool_registry = tool_registry
        self.system_prompt_processor_registry = system_prompt_processor_registry
        self.llm_factory = llm_factory
        
        self.bootstrap_steps: List[BaseBootstrapStep] = [
            AgentRuntimeQueueInitializationStep(), # UPDATED CLASS NAME
            ToolInitializationStep(tool_registry=self.tool_registry),
            SystemPromptProcessingStep(system_prompt_processor_registry=self.system_prompt_processor_registry),
            LLMConfigFinalizationStep(), 
            LLMInstanceCreationStep(llm_factory=self.llm_factory)
        ]
        logger.info(f"BootstrapAgentEventHandler initialized with {len(self.bootstrap_steps)} steps, starting with AgentRuntimeQueueInitializationStep.") # UPDATED Log

    async def handle(self,
                     event: BootstrapAgentEvent,
                     context: 'AgentContext') -> None:
        if not isinstance(event, BootstrapAgentEvent): # pragma: no cover
            logger.warning(f"BootstrapAgentEventHandler received non-BootstrapAgentEvent: {type(event)}. Skipping.")
            return

        agent_id = context.agent_id
        logger.info(f"Agent '{agent_id}': Starting orchestrated bootstrap process via BootstrapAgentEventHandler.")
        
        phase_manager = context.state.phase_manager_ref
        if not phase_manager: # pragma: no cover
            critical_msg = f"Agent '{agent_id}': AgentPhaseManager not found in context.state. Bootstrap cannot proceed with phase notifications or robust error reporting."
            logger.critical(critical_msg)
            return

        all_steps_succeeded = True
        for step_index, step_instance in enumerate(self.bootstrap_steps):
            step_name = step_instance.__class__.__name__ # This will now be 'AgentRuntimeQueueInitializationStep' for the first step
            logger.debug(f"Agent '{agent_id}': Executing bootstrap step {step_index + 1}/{len(self.bootstrap_steps)}: {step_name}")
            
            success = await step_instance.execute(context, phase_manager)
            
            if not success:
                logger.error(f"Agent '{agent_id}': Bootstrap step {step_name} failed. Halting bootstrap process.")
                all_steps_succeeded = False
                
                if step_name == "AgentRuntimeQueueInitializationStep": # UPDATED string to match new class name
                    phase_manager.notify_error_occurred(
                        f"Critical bootstrap failure at {step_name}",
                        f"Agent '{agent_id}' failed during {step_name}. Check logs for details."
                    )
                    logger.critical(f"Agent '{agent_id}': {step_name} failed, which is critical for error reporting. Manual phase notification triggered.")
                else:
                    # For other steps, they are expected to enqueue AgentErrorEvent.
                    # If the input_event_queues are available (they should be after AgentRuntimeQueueInitializationStep),
                    # we can attempt to enqueue a fallback error if not already handled.
                    # However, for now, this handler relies on the step itself or an exception bubbling up.
                    pass
                break 

        if all_steps_succeeded:
            logger.info(f"Agent '{agent_id}': All bootstrap steps completed successfully. Agent is ready. Enqueuing AgentReadyEvent.")
            if context.state.input_event_queues: 
                await context.state.input_event_queues.enqueue_internal_system_event(AgentReadyEvent())
            else: # pragma: no cover
                logger.error(f"Agent '{agent_id}': Bootstrap supposedly succeeded, but input_event_queues are not available. Cannot enqueue AgentReadyEvent.")
                phase_manager.notify_error_occurred(
                    "Bootstrap inconsistency: All steps reported success, but queues are missing.",
                    "This indicates a potential logic error in the bootstrap sequence or AgentRuntimeQueueInitializationStep."
                )
        else:
            logger.warning(f"Agent '{agent_id}': Bootstrap process did not complete successfully. AgentReadyEvent not sent.")

