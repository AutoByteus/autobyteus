# file: autobyteus/autobyteus/agent/handlers/llm_complete_response_received_event_handler.py
import logging
from typing import TYPE_CHECKING, Optional 

from autobyteus.agent.handlers.base_event_handler import AgentEventHandler
from autobyteus.agent.events import LLMCompleteResponseReceivedEvent 
from autobyteus.llm.utils.response_types import CompleteResponse
from autobyteus.agent.llm_response_processor import BaseLLMResponseProcessor
from autobyteus.tools.usage.parsers.exceptions import ToolUsageParseException


if TYPE_CHECKING:
    from autobyteus.agent.context import AgentContext 
    from autobyteus.agent.events.notifiers import AgentExternalEventNotifier 


logger = logging.getLogger(__name__)

class LLMCompleteResponseReceivedEventHandler(AgentEventHandler):
    """
    Handles LLMCompleteResponseReceivedEvents.
    It attempts to process the response using configured LLMResponseProcessor instances.
    If no processor handles the response (e.g., to extract a tool call),
    it emits an agent data event via the notifier with the LLM's complete response.
    """
    def __init__(self):
        logger.info("LLMCompleteResponseReceivedEventHandler initialized.")

    async def handle(self,
                     event: LLMCompleteResponseReceivedEvent, 
                     context: 'AgentContext') -> None: 
        complete_response: CompleteResponse = event.complete_response
        complete_response_text = complete_response.content
        complete_response_reasoning = complete_response.reasoning
        is_error_response = getattr(event, 'is_error', False) 

        agent_id = context.agent_id 
        logger.info(
            f"Agent '{agent_id}' handling LLMCompleteResponseReceivedEvent. "
            f"Response Length: {len(complete_response_text)}, Reasoning Length: {len(complete_response_reasoning) if complete_response_reasoning else 0}, "
            f"IsErrorFlagged: {is_error_response}, TokenUsage: {complete_response.usage}"
        )
        if complete_response_reasoning:
            logger.debug(f"Agent '{agent_id}' received LLM reasoning for processing:\n---\n{complete_response_reasoning}\n---")
        
        # Changed from .debug to .info as per user request
        logger.info(f"Agent '{agent_id}' received full LLM content for processing:\n---\n{complete_response_text}\n---")

        any_processor_took_action = False
        
        notifier: Optional['AgentExternalEventNotifier'] = None
        if context.phase_manager:
            notifier = context.phase_manager.notifier
        
        if not notifier: # pragma: no cover
            logger.error(f"Agent '{agent_id}': Notifier not available in LLMCompleteResponseReceivedEventHandler. Cannot emit complete response event.")

        if not is_error_response:
            processor_instances_to_try = context.config.llm_response_processors
            if not processor_instances_to_try: 
                logger.debug(
                    f"Agent '{agent_id}': No LLM response processors configured in agent config. "
                    f"Proceeding to treat LLM response as output for this leg."
                )
            else:
                processor_names = [p.get_name() for p in processor_instances_to_try]
                logger.debug(f"Agent '{agent_id}': Attempting LLM response processing with: {processor_names}")
                for processor_instance in processor_instances_to_try:
                    processor_name_for_log: str = "unknown"
                    try:
                        if not isinstance(processor_instance, BaseLLMResponseProcessor):
                            logger.error(f"Agent '{agent_id}': Invalid LLM response processor type in config: {type(processor_instance)}. Skipping.")
                            continue

                        processor_name_for_log = processor_instance.get_name()
                        logger.debug(f"Agent '{agent_id}': Attempting to process with LLMResponseProcessor '{processor_name_for_log}'.")
                        
                        # The processor will now receive a response with clean content
                        handled_by_this_processor = await processor_instance.process_response(
                            response=complete_response, 
                            context=context, 
                            triggering_event=event
                        ) 
                        
                        if handled_by_this_processor:
                            any_processor_took_action = True
                            logger.info(
                                f"Agent '{agent_id}': LLMResponseProcessor '{processor_name_for_log}' "
                                f"handled the response. This LLM response "
                                f"will not be emitted as a complete response by this handler instance."
                            )
                            break 
                        else:
                            logger.debug(f"Agent '{agent_id}': LLMResponseProcessor '{processor_name_for_log}' did not handle the response.")

                    except ToolUsageParseException as e_parse:
                        # This is the key change: Catch the specific parsing exception
                        logger.warning(f"Agent '{agent_id}': LLMResponseProcessor '{processor_name_for_log}' failed to parse tool usage: {e_parse}")
                        if notifier:
                            notifier.notify_agent_error_output_generation( 
                                error_source=f"LLMResponseProcessor.{processor_name_for_log}",
                                error_message="The model's response contained a malformed tool call that could not be understood.",
                                error_details=str(e_parse)
                            )
                        any_processor_took_action = True # Mark as handled to prevent printing raw response
                        break

                    except Exception as e: # pragma: no cover
                        logger.error(f"Agent '{agent_id}': Error while using LLMResponseProcessor '{processor_name_for_log}': {e}. This processor is skipped.", exc_info=True)
                        if notifier:
                            notifier.notify_agent_error_output_generation( 
                                error_source=f"LLMResponseProcessor.{processor_name_for_log}",
                                error_message=str(e)
                            )
        else:
            logger.info(
                f"Agent '{agent_id}': LLMCompleteResponseReceivedEvent was marked as an error response. "
                f"Skipping LLMResponseProcessor attempts."
            )

        if not any_processor_took_action:
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
                    # The complete_response object now contains both content and reasoning
                    notifier.notify_agent_data_assistant_complete_response(complete_response) 
                    logger.debug(f"Agent '{agent_id}' emitted AGENT_DATA_ASSISTANT_COMPLETE_RESPONSE event.")
                except Exception as e_notify: # pragma: no cover
                    logger.error(f"Agent '{agent_id}': Error emitting AGENT_DATA_ASSISTANT_COMPLETE_RESPONSE: {e_notify}", exc_info=True)
