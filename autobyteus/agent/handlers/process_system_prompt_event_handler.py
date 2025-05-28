# file: autobyteus/autobyteus/agent/handlers/process_system_prompt_event_handler.py
import logging
from typing import TYPE_CHECKING, Optional

from autobyteus.agent.handlers.base_event_handler import AgentEventHandler
from autobyteus.agent.events import ProcessSystemPromptEvent, FinalizeLLMConfigEvent, AgentErrorEvent

if TYPE_CHECKING:
    from autobyteus.agent.context import AgentContext 
    from autobyteus.agent.system_prompt_processor import SystemPromptProcessorRegistry, BaseSystemPromptProcessor

logger = logging.getLogger(__name__)

class ProcessSystemPromptEventHandler(AgentEventHandler):
    """
    Handles the ProcessSystemPromptEvent. This handler is responsible for:
    1. Retrieving the system prompt template from agent configuration.
    2. Processing the template using configured SystemPromptProcessors, providing them
       with tool instances from the agent's runtime state and the agent context.
    3. Storing the processed system prompt in the agent's runtime state.
    4. Enqueuing a FinalizeLLMConfigEvent to proceed with LLM setup.
    """

    def __init__(self, system_prompt_processor_registry: 'SystemPromptProcessorRegistry'):
        if system_prompt_processor_registry is None:
            raise ValueError("ProcessSystemPromptEventHandler requires a SystemPromptProcessorRegistry instance.")
            
        self.system_prompt_processor_registry = system_prompt_processor_registry
        logger.info("ProcessSystemPromptEventHandler initialized.")

    async def handle(self,
                     event: ProcessSystemPromptEvent,
                     context: 'AgentContext') -> None:
        if not isinstance(event, ProcessSystemPromptEvent):
            logger.warning(f"ProcessSystemPromptEventHandler received non-ProcessSystemPromptEvent: {type(event)}. Skipping.")
            return

        agent_id = context.agent_id # Using convenience property
        logger.info(f"Agent '{agent_id}': Handling ProcessSystemPromptEvent.")

        try:
            current_system_prompt = context.definition.system_prompt # Using convenience property
            processor_names_to_apply = context.definition.system_prompt_processor_names # Using convenience property
            
            tool_instances_for_processor = context.tool_instances 

            if not processor_names_to_apply:
                logger.debug(f"Agent '{agent_id}': No system prompt processors configured. Using system prompt template as is.")
            else:
                logger.debug(f"Agent '{agent_id}': Applying system prompt processors: {processor_names_to_apply}")
                for processor_name in processor_names_to_apply:
                    processor_instance: Optional['BaseSystemPromptProcessor'] = self.system_prompt_processor_registry.get_processor(processor_name)
                    if processor_instance:
                        try:
                            logger.debug(f"Agent '{agent_id}': Applying system prompt processor '{processor_name}' (class: {processor_instance.__class__.__name__}).")
                            current_system_prompt = processor_instance.process(
                                system_prompt=current_system_prompt,
                                tool_instances=tool_instances_for_processor, 
                                agent_id=agent_id,
                                context=context # Pass the full context
                            )
                            logger.info(f"Agent '{agent_id}': System prompt processor '{processor_name}' applied successfully.")
                        except Exception as e_proc:
                            logger.error(f"Agent '{agent_id}': Error applying system prompt processor '{processor_name}': {e_proc}. "
                                         f"Continuing with prompt from before this processor.", exc_info=True)
                    else:
                        logger.warning(f"Agent '{agent_id}': System prompt processor name '{processor_name}' not found in registry. Skipping.")
            
            logger.debug(f"Agent '{agent_id}': Final processed system prompt after all processors:\n---\n{current_system_prompt}\n---")

            context.processed_system_prompt = current_system_prompt 
            logger.info(f"Agent '{agent_id}': System prompt processed and stored in state. Final prompt (first 100 chars): '{current_system_prompt[:100]}...'")

            await context.queues.enqueue_internal_system_event(FinalizeLLMConfigEvent()) 
            logger.debug(f"Agent '{agent_id}': Enqueued FinalizeLLMConfigEvent.")

        except Exception as e:
            error_message = f"Agent '{agent_id}': Failed during system prompt processing: {e}"
            logger.error(error_message, exc_info=True)
            await context.queues.enqueue_internal_system_event( 
                AgentErrorEvent(error_message=error_message, exception_details=str(e))
            )

