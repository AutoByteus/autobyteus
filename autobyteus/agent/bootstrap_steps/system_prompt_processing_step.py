# file: autobyteus/autobyteus/agent/bootstrap_steps/system_prompt_processing_step.py
import logging
from typing import TYPE_CHECKING

from .base_bootstrap_step import BaseBootstrapStep
from autobyteus.agent.events import AgentErrorEvent
from autobyteus.agent.system_prompt_processor.base_processor import BaseSystemPromptProcessor

if TYPE_CHECKING:
    from autobyteus.agent.context import AgentContext
    from autobyteus.agent.phases import AgentPhaseManager

logger = logging.getLogger(__name__)

class SystemPromptProcessingStep(BaseBootstrapStep):
    """
    Bootstrap step for processing the agent's system prompt and setting it
    on the pre-initialized LLM instance.
    If any configured processor fails, this entire step is considered failed.
    """
    def __init__(self):
        logger.debug("SystemPromptProcessingStep initialized.")

    async def execute(self,
                      context: 'AgentContext',
                      phase_manager: 'AgentPhaseManager') -> bool:
        agent_id = context.agent_id
        # The phase is now managed by the AgentBootstrapper.
        logger.info(f"Agent '{agent_id}': Executing SystemPromptProcessingStep.")

        try:
            # The LLM instance is now expected to be present from the start.
            llm_instance = context.llm_instance
            if not llm_instance:
                raise ValueError("LLM instance not found in agent state. It must be provided in AgentConfig.")

            current_system_prompt = context.config.system_prompt
            logger.debug(f"Agent '{agent_id}': Retrieved base system prompt from agent config.")
            
            processor_instances = context.config.system_prompt_processors
            tool_instances_for_processor = context.tool_instances

            if not processor_instances:
                logger.debug(f"Agent '{agent_id}': No system prompt processors configured. Using system prompt as is.")
            else:
                logger.debug(f"Agent '{agent_id}': Found {len(processor_instances)} configured system prompt processors. Applying sequentially.")
                for processor_instance in processor_instances:
                    if not isinstance(processor_instance, BaseSystemPromptProcessor):
                        error_message = f"Agent '{agent_id}': Invalid system prompt processor configuration type: {type(processor_instance)}. Expected BaseSystemPromptProcessor."
                        logger.error(error_message)
                        raise TypeError(error_message)
                    
                    processor_name = processor_instance.get_name()
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
                        error_message = f"Agent '{agent_id}': Error applying system prompt processor '{processor_name}': {e_proc}"
                        logger.error(error_message, exc_info=True)
                        if context.state.input_event_queues:
                            await context.state.input_event_queues.enqueue_internal_system_event(
                                AgentErrorEvent(error_message=error_message, exception_details=str(e_proc))
                            )
                        return False # Signal failure of the entire step
            
            context.state.processed_system_prompt = current_system_prompt
            
            # --- New Logic: Set the prompt on the existing LLM instance ---
            if hasattr(llm_instance, 'configure_system_prompt') and callable(getattr(llm_instance, 'configure_system_prompt')):
                llm_instance.configure_system_prompt(current_system_prompt)
                logger.info(f"Agent '{agent_id}': Final processed system prompt configured on LLM instance. Final length: {len(current_system_prompt)}.")
            else:
                # This path should ideally not be taken if all LLMs inherit from the updated BaseLLM.
                # It's kept as a fallback with a strong warning.
                logger.warning(f"Agent '{agent_id}': LLM instance ({llm_instance.__class__.__name__}) does not have a 'configure_system_prompt' method. "
                               f"The system prompt cannot be dynamically updated on the LLM instance after initialization. This may lead to incorrect agent behavior.")

            logger.info(f"Agent '{agent_id}': Final processed system prompt:\n---\n{current_system_prompt}\n---")
            return True
        except Exception as e: # Catches other errors in the step setup itself
            error_message = f"Agent '{agent_id}': Critical failure during system prompt processing step: {e}"
            logger.error(error_message, exc_info=True)
            if context.state.input_event_queues:
                await context.input_event_queues.enqueue_internal_system_event(
                    AgentErrorEvent(error_message=error_message, exception_details=str(e))
                )
            return False
