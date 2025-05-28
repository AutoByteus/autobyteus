# file: autobyteus/autobyteus/agent/handlers/llm_complete_response_received_event_handler.py
import logging
from typing import TYPE_CHECKING 

from autobyteus.agent.handlers.base_event_handler import AgentEventHandler
from autobyteus.agent.events import LLMCompleteResponseReceivedEvent 
from autobyteus.agent.events import END_OF_STREAM_SENTINEL 
from autobyteus.llm.utils.response_types import CompleteResponse

from autobyteus.agent.llm_response_processor import default_llm_response_processor_registry


if TYPE_CHECKING:
    from autobyteus.agent.context import AgentContext # Composite AgentContext
    from autobyteus.agent.llm_response_processor.base_processor import BaseLLMResponseProcessor


logger = logging.getLogger(__name__)

class LLMCompleteResponseReceivedEventHandler(AgentEventHandler):
    """
    Handles LLMCompleteResponseReceivedEvents.
    (Docstring regarding behavior remains the same)
    """
    def __init__(self):
        logger.info("LLMCompleteResponseReceivedEventHandler initialized.")
        self.llm_response_processor_registry = default_llm_response_processor_registry

    async def handle(self,
                     event: LLMCompleteResponseReceivedEvent, 
                     context: 'AgentContext') -> None: # context is composite
        complete_response_text = event.complete_response_text
        is_error_response = getattr(event, 'is_error', False) 

        agent_id = context.agent_id # Using convenience property

        logger.info(
            f"Agent '{agent_id}' handling LLMCompleteResponseReceivedEvent. "
            f"Response Length: {len(complete_response_text)}, IsErrorFlagged: {is_error_response}"
        )
        logger.debug(f"Agent '{agent_id}' received full LLM response text for processing:\n---\n{complete_response_text}\n---")

        any_processor_took_action = False
        final_message_queue = context.queues.assistant_final_message_queue # Using convenience property

        if not is_error_response:
            # Access definition via convenience property or context.config
            processor_names_to_try = context.definition.llm_response_processor_names
            if not processor_names_to_try: 
                logger.debug(
                    f"Agent '{agent_id}': No llm_response_processor_names configured in agent definition. "
                    f"Proceeding to treat LLM response as final output for this leg."
                )
            else:
                logger.debug(f"Agent '{agent_id}': Attempting LLM response processing with: {processor_names_to_try}")
                for processor_name in processor_names_to_try:
                    processor_definition = self.llm_response_processor_registry.get_processor_definition(processor_name)
                    
                    if processor_definition:
                        processor_class = processor_definition.processor_class
                        processor_instance: 'BaseLLMResponseProcessor' = processor_class() 
                        try:
                            logger.debug(
                                f"Agent '{agent_id}': Attempting to process with "
                                f"LLMResponseProcessor '{processor_name}' (class: {processor_class.__name__})."
                            )
                            
                            # Pass the composite context to the processor
                            handled_by_this_processor = await processor_instance.process_response(
                                complete_response_text, context 
                            ) 
                            
                            if handled_by_this_processor:
                                any_processor_took_action = True
                                logger.info(
                                    f"Agent '{agent_id}': LLMResponseProcessor '{processor_name}' "
                                    f"handled the response. This LLM response "
                                    f"will not be sent to the final message queue by this handler instance."
                                )
                                break 
                            else:
                                logger.debug(
                                    f"Agent '{agent_id}': LLMResponseProcessor '{processor_name}' "
                                    f"did not handle the response."
                                )
                        except Exception as e:
                            logger.error(
                                f"Agent '{agent_id}': Error occurred while using "
                                f"LLMResponseProcessor '{processor_name}': {e}. This processor is skipped.", exc_info=True
                            )
                    else:
                        logger.warning(
                            f"Agent '{agent_id}': LLMResponseProcessor name '{processor_name}' "
                            f"defined in agent_definition not found in registry. Skipping this processor."
                        )
        else:
            logger.info(
                f"Agent '{agent_id}': LLMCompleteResponseReceivedEvent was marked as an error response. "
                f"Skipping LLMResponseProcessor attempts."
            )

        if not any_processor_took_action:
            final_response = CompleteResponse(content=complete_response_text)
            
            if is_error_response:
                logger.info(
                    f"Agent '{agent_id}' publishing a received error message to the "
                    f"assistant_final_message_queue: '{complete_response_text[:100]}...'"
                )
            else:
                logger.info(
                    f"Agent '{agent_id}': No LLMResponseProcessor handled the response. "
                    f"Publishing the current LLM response as a final message for this leg "
                    f"to assistant_final_message_queue: '{complete_response_text[:100]}...'"
                )
            
            await final_message_queue.put(final_response)
            await final_message_queue.put(END_OF_STREAM_SENTINEL)
            logger.debug(
                f"Agent '{agent_id}' placed CompleteResponse and sentinel into assistant_final_message_queue."
            )

