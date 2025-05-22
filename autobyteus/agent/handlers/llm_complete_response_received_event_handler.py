# file: autobyteus/autobyteus/agent/handlers/llm_complete_response_received_event_handler.py
import logging
from typing import TYPE_CHECKING 

from autobyteus.agent.handlers.base_event_handler import AgentEventHandler
from autobyteus.agent.events import LLMCompleteResponseReceivedEvent # MODIFIED IMPORT
from autobyteus.agent.events import END_OF_STREAM_SENTINEL # MODIFIED IMPORT

from autobyteus.agent.llm_response_processor import default_llm_response_processor_registry


if TYPE_CHECKING:
    from autobyteus.agent.context import AgentContext # MODIFIED IMPORT
    from autobyteus.agent.llm_response_processor.base_processor import BaseLLMResponseProcessor


logger = logging.getLogger(__name__)

class LLMCompleteResponseReceivedEventHandler(AgentEventHandler):
    """
    Handles LLMCompleteResponseReceivedEvents.

    Its primary responsibilities are:
    1. If the received event's content is not an error:
        a. Attempt to process the LLM's response using configured `LLMResponseProcessors`
           (e.g., to detect tool calls).
        b. If a processor handles the response (e.g., enqueues a `PendingToolInvocationEvent`),
           this handler considers the current LLM response as an intermediate step (a tool request)
           and does *not* publish it to the `assistant_final_message_queue`.
    2. If the event's content *is* an error (propagated from a previous stage), or if no
       `LLMResponseProcessor` handles the non-error response:
        a. The `complete_response_text` is considered the final output for this interaction leg.
        b. This text (whether it's a final answer or an error message) is published to the
           `assistant_final_message_queue`, followed by an `END_OF_STREAM_SENTINEL`.
    """
    def __init__(self):
        logger.info("LLMCompleteResponseReceivedEventHandler initialized.")
        self.llm_response_processor_registry = default_llm_response_processor_registry

    async def handle(self,
                     event: LLMCompleteResponseReceivedEvent, 
                     context: 'AgentContext') -> None:
        complete_response_text = event.complete_response_text
        is_error_response = getattr(event, 'is_error', False) 

        logger.info(
            f"Agent '{context.agent_id}' handling LLMCompleteResponseReceivedEvent. "
            f"Response Length: {len(complete_response_text)}, IsErrorFlagged: {is_error_response}"
        )

        any_processor_took_action = False
        final_message_queue = context.queues.assistant_final_message_queue

        if not is_error_response:
            processor_names_to_try = context.definition.llm_response_processor_names
            if not processor_names_to_try: 
                logger.debug(
                    f"Agent '{context.agent_id}': No llm_response_processor_names configured in agent definition. "
                    f"Proceeding to treat LLM response as final output for this leg."
                )
            else:
                logger.debug(f"Agent '{context.agent_id}': Attempting LLM response processing with: {processor_names_to_try}")
                for processor_name in processor_names_to_try:
                    processor_definition = self.llm_response_processor_registry.get_processor_definition(processor_name)
                    
                    if processor_definition:
                        processor_class = processor_definition.processor_class
                        processor_instance: 'BaseLLMResponseProcessor' = processor_class() 
                        try:
                            logger.debug(
                                f"Agent '{context.agent_id}': Attempting to process with "
                                f"LLMResponseProcessor '{processor_name}' (class: {processor_class.__name__})."
                            )
                            
                            handled_by_this_processor = await processor_instance.process_response(
                                complete_response_text, context
                            ) 
                            
                            if handled_by_this_processor:
                                any_processor_took_action = True
                                logger.info(
                                    f"Agent '{context.agent_id}': LLMResponseProcessor '{processor_name}' "
                                    f"handled the response (e.g., enqueued a tool event). This LLM response "
                                    f"will not be sent to the final message queue by this handler instance."
                                )
                                break 
                            else:
                                logger.debug(
                                    f"Agent '{context.agent_id}': LLMResponseProcessor '{processor_name}' "
                                    f"did not handle the response."
                                )
                        except Exception as e:
                            logger.error(
                                f"Agent '{context.agent_id}': Error occurred while using "
                                f"LLMResponseProcessor '{processor_name}': {e}. This processor is skipped.", exc_info=True
                            )
                    else:
                        logger.warning(
                            f"Agent '{context.agent_id}': LLMResponseProcessor name '{processor_name}' "
                            f"defined in agent_definition not found in registry. Skipping this processor."
                        )
        else:
            logger.info(
                f"Agent '{context.agent_id}': LLMCompleteResponseReceivedEvent was marked as an error response. "
                f"Skipping LLMResponseProcessor attempts. The error content will be published to the final message queue."
            )

        if not any_processor_took_action:
            if is_error_response:
                logger.info(
                    f"Agent '{context.agent_id}' publishing a received error message to the "
                    f"assistant_final_message_queue: '{complete_response_text[:100]}...'"
                )
            else:
                logger.info(
                    f"Agent '{context.agent_id}': No LLMResponseProcessor handled the response. "
                    f"Publishing the current LLM response as a final message for this leg "
                    f"to assistant_final_message_queue: '{complete_response_text[:100]}...'"
                )
            
            await final_message_queue.put(complete_response_text)
            await final_message_queue.put(END_OF_STREAM_SENTINEL)
            logger.debug(
                f"Agent '{context.agent_id}' placed response and sentinel into assistant_final_message_queue."
            )
