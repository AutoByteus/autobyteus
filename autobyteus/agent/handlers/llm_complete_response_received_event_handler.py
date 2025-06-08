# file: autobyteus/autobyteus/agent/handlers/llm_complete_response_received_event_handler.py
import logging
from typing import TYPE_CHECKING, Optional 

from autobyteus.agent.handlers.base_event_handler import AgentEventHandler
from autobyteus.agent.events import LLMCompleteResponseReceivedEvent 
from autobyteus.llm.utils.response_types import CompleteResponse
from autobyteus.agent.llm_response_processor import default_llm_response_processor_registry


if TYPE_CHECKING:
    from autobyteus.agent.context import AgentContext 
    from autobyteus.agent.llm_response_processor.base_processor import BaseLLMResponseProcessor
    from autobyteus.agent.events.notifiers import AgentExternalEventNotifier 


logger = logging.getLogger(__name__)

class LLMCompleteResponseReceivedEventHandler(AgentEventHandler):
    """
    Handles LLMCompleteResponseReceivedEvents.
    It attempts to process the response using configured LLMResponseProcessors.
    If no processor handles the response (e.g., to extract a tool call),
    it emits an agent data event via the notifier with the LLM's complete response.
    """
    def __init__(self):
        logger.info("LLMCompleteResponseReceivedEventHandler initialized.")
        self.llm_response_processor_registry = default_llm_response_processor_registry

    async def handle(self,
                     event: LLMCompleteResponseReceivedEvent, 
                     context: 'AgentContext') -> None: 
        complete_response_text = event.complete_response_text
        is_error_response = getattr(event, 'is_error', False) 

        agent_id = context.agent_id 
        logger.info(
            f"Agent '{agent_id}' handling LLMCompleteResponseReceivedEvent. "
            f"Response Length: {len(complete_response_text)}, IsErrorFlagged: {is_error_response}"
        )
        logger.debug(f"Agent '{agent_id}' received full LLM response text for processing:\n---\n{complete_response_text}\n---")

        any_processor_took_action = False
        
        notifier: Optional['AgentExternalEventNotifier'] = None
        if context.phase_manager:
            notifier = context.phase_manager.notifier
        
        if not notifier: # pragma: no cover
            logger.error(f"Agent '{agent_id}': Notifier not available in LLMCompleteResponseReceivedEventHandler. Cannot emit complete response event.")

        if not is_error_response:
            processor_names_to_try = context.definition.llm_response_processor_names
            if not processor_names_to_try: 
                logger.debug(
                    f"Agent '{agent_id}': No llm_response_processor_names configured in agent definition. "
                    f"Proceeding to treat LLM response as output for this leg."
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
                            
                            handled_by_this_processor = await processor_instance.process_response(
                                complete_response_text, context 
                            ) 
                            
                            if handled_by_this_processor:
                                any_processor_took_action = True
                                logger.info(
                                    f"Agent '{agent_id}': LLMResponseProcessor '{processor_name}' "
                                    f"handled the response. This LLM response "
                                    f"will not be emitted as a complete response by this handler instance."
                                )
                                break 
                            else:
                                logger.debug(
                                    f"Agent '{agent_id}': LLMResponseProcessor '{processor_name}' "
                                    f"did not handle the response."
                                )
                        except Exception as e: # pragma: no cover
                            logger.error(
                                f"Agent '{agent_id}': Error occurred while using "
                                f"LLMResponseProcessor '{processor_name}': {e}. This processor is skipped.", exc_info=True
                            )
                            if notifier:
                                notifier.notify_agent_error_output_generation( 
                                    error_source=f"LLMResponseProcessor.{processor_name}",
                                    error_message=str(e)
                                )
                    else: # pragma: no cover
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
            # Assuming the event carries usage info if available, or reconstruct CompleteResponse if needed
            # For simplicity, using the text directly. If usage info is needed here, event should carry it or state should have it.
            complete_response_obj = CompleteResponse(content=complete_response_text) 
            
            if is_error_response:
                logger.info(
                    f"Agent '{agent_id}' emitting a received error message as a complete response: '{complete_response_text[:100]}...'"
                )
            else:
                logger.info(
                    f"Agent '{agent_id}': No LLMResponseProcessor handled the response. "
                    f"Emitting the current LLM response as a complete response for this leg."
                )
            
            if notifier:
                try:
                    # UPDATED: Call renamed notifier method
                    notifier.notify_agent_data_assistant_complete_response(complete_response_obj) 
                    logger.debug(
                        f"Agent '{agent_id}' emitted AGENT_DATA_ASSISTANT_COMPLETE_RESPONSE event." # Log updated event type
                    )
                except Exception as e_notify: # pragma: no cover
                    logger.error(f"Agent '{agent_id}': Error emitting AGENT_DATA_ASSISTANT_COMPLETE_RESPONSE: {e_notify}", exc_info=True)
