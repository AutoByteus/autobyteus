# file: autobyteus/autobyteus/agent/bootstrap_steps/system_prompt_processing_step.py
import logging
from typing import TYPE_CHECKING, Optional

from .base_bootstrap_step import BaseBootstrapStep
from autobyteus.agent.events import AgentErrorEvent

if TYPE_CHECKING:
    from autobyteus.agent.context import AgentContext
    from autobyteus.agent.context.agent_phase_manager import AgentPhaseManager
    from autobyteus.agent.system_prompt_processor import SystemPromptProcessorRegistry, BaseSystemPromptProcessor

logger = logging.getLogger(__name__)

class SystemPromptProcessingStep(BaseBootstrapStep):
    """
    Bootstrap step for processing the agent's system prompt.
    If any configured processor fails, this entire step is considered failed.
    """
    def __init__(self, system_prompt_processor_registry: 'SystemPromptProcessorRegistry'):
        if system_prompt_processor_registry is None: # pragma: no cover
            raise ValueError("SystemPromptProcessingStep requires a SystemPromptProcessorRegistry instance.")
        self.system_prompt_processor_registry = system_prompt_processor_registry
        logger.debug("SystemPromptProcessingStep initialized.")

    async def execute(self,
                      context: 'AgentContext',
                      phase_manager: 'AgentPhaseManager') -> bool:
        agent_id = context.agent_id
        phase_manager.notify_initializing_prompt()
        logger.info(f"Agent '{agent_id}': Executing SystemPromptProcessingStep.")

        try:
            current_system_prompt = context.specification.system_prompt
            logger.debug(f"Agent '{agent_id}': Retrieved system prompt from agent specification.")
            
            processor_names_to_apply = context.specification.system_prompt_processor_names
            tool_instances_for_processor = context.tool_instances # Assumes tools are already initialized

            if not processor_names_to_apply:
                logger.debug(f"Agent '{agent_id}': No system prompt processors configured. Using system prompt as is.")
            else:
                logger.debug(f"Agent '{agent_id}': Applying system prompt processors: {processor_names_to_apply}")
                for processor_name in processor_names_to_apply:
                    processor_instance: Optional['BaseSystemPromptProcessor'] = self.system_prompt_processor_registry.get_processor(processor_name)
                    if processor_instance:
                        try:
                            logger.debug(f"Agent '{agent_id}': Applying system prompt processor '{processor_name}'.")
                            current_system_prompt = processor_instance.process(
                                system_prompt=current_system_prompt,
                                tool_instances=tool_instances_for_processor,
                                agent_id=agent_id,
                                context=context
                            )
                            logger.info(f"Agent '{agent_id}': System prompt processor '{processor_name}' applied successfully.")
                        except Exception as e_proc: 
                            # If an individual processor fails, the whole step fails.
                            error_message = f"Agent '{agent_id}': Error applying system prompt processor '{processor_name}': {e_proc}"
                            logger.error(error_message, exc_info=True)
                            await context.input_event_queues.enqueue_internal_system_event(
                                AgentErrorEvent(error_message=error_message, exception_details=str(e_proc))
                            )
                            return False # Signal failure of the entire step
                    else: # pragma: no cover
                        # If a processor is configured but not found, this is a configuration error, step should fail.
                        error_message = f"Agent '{agent_id}': System prompt processor '{processor_name}' not found in registry. This is a configuration error."
                        logger.error(error_message)
                        await context.input_event_queues.enqueue_internal_system_event(
                            AgentErrorEvent(error_message=error_message, exception_details=None)
                        )
                        return False
            
            context.state.processed_system_prompt = current_system_prompt
            logger.info(f"Agent '{agent_id}': System prompt processed. Final length: {len(current_system_prompt)}.")
            logger.info(f"Agent '{agent_id}': Final processed system prompt:\n---\n{current_system_prompt}\n---")
            return True
        except Exception as e: # Catches other errors in the step setup itself
            error_message = f"Agent '{agent_id}': Critical failure during system prompt processing step setup: {e}"
            logger.error(error_message, exc_info=True)
            await context.input_event_queues.enqueue_internal_system_event(
                AgentErrorEvent(error_message=error_message, exception_details=str(e))
            )
            return False
