# file: autobyteus/autobyteus/agent/handlers/bootstrap_agent_event_handler.py
import logging
from typing import TYPE_CHECKING, List

from autobyteus.agent.handlers.base_event_handler import AgentEventHandler
from autobyteus.agent.events import BootstrapAgentEvent, AgentReadyEvent # MODIFIED: AgentReadyEvent
# AgentErrorEvent is enqueued by individual steps now

# Import bootstrap steps
from autobyteus.agent.bootstrap_steps import (
    BaseBootstrapStep,
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
    """

    def __init__(self,
                 tool_registry: 'ToolRegistry',
                 system_prompt_processor_registry: 'SystemPromptProcessorRegistry',
                 llm_factory: 'LLMFactory'):
        
        # Store dependencies needed by steps
        self.tool_registry = tool_registry
        self.system_prompt_processor_registry = system_prompt_processor_registry
        self.llm_factory = llm_factory
        
        # Define the sequence of bootstrap steps
        self.bootstrap_steps: List[BaseBootstrapStep] = [
            ToolInitializationStep(tool_registry=self.tool_registry),
            SystemPromptProcessingStep(system_prompt_processor_registry=self.system_prompt_processor_registry),
            LLMConfigFinalizationStep(), # Takes no direct dependencies in constructor
            LLMInstanceCreationStep(llm_factory=self.llm_factory)
        ]
        logger.info(f"BootstrapAgentEventHandler initialized with {len(self.bootstrap_steps)} steps.")

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
            logger.critical(f"Agent '{agent_id}': AgentPhaseManager not found in context.state. Bootstrap cannot proceed with phase notifications.")
            # This is a critical setup error. Individual steps might also fail or log this.
            # For robustness, BootstrapAgentEventHandler could enqueue an error here too,
            # but steps are designed to do so. If phase_manager is None, steps will fail.
            # No AgentErrorEvent enqueued here as steps will handle their failures.
            return

        for step_index, step_instance in enumerate(self.bootstrap_steps):
            step_name = step_instance.__class__.__name__
            logger.debug(f"Agent '{agent_id}': Executing bootstrap step {step_index + 1}/{len(self.bootstrap_steps)}: {step_name}")
            
            success = await step_instance.execute(context, phase_manager)
            
            if not success:
                logger.error(f"Agent '{agent_id}': Bootstrap step {step_name} failed. Halting bootstrap process.")
                # The step itself should have enqueued an AgentErrorEvent.
                return # Stop further steps

        # If all steps completed successfully
        logger.info(f"Agent '{agent_id}': All bootstrap steps completed successfully. Agent is ready. Enqueuing AgentReadyEvent.") # MODIFIED log
        await context.input_event_queues.enqueue_internal_system_event(AgentReadyEvent()) # MODIFIED: Enqueue AgentReadyEvent
