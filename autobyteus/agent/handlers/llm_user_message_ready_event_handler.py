# file: autobyteus/autobyteus/agent/handlers/llm_user_message_ready_event_handler.py
import logging
import traceback
from typing import TYPE_CHECKING, cast, Optional

from autobyteus.agent.handlers.base_event_handler import AgentEventHandler
from autobyteus.agent.events import LLMUserMessageReadyEvent, LLMCompleteResponseReceivedEvent 
from autobyteus.llm.user_message import LLMUserMessage
from autobyteus.llm.utils.response_types import ChunkResponse, CompleteResponse
from autobyteus.llm.utils.token_usage import TokenUsage

if TYPE_CHECKING:
    from autobyteus.agent.context import AgentContext
    from autobyteus.agent.events.notifiers import AgentExternalEventNotifier 

logger = logging.getLogger(__name__)

class LLMUserMessageReadyEventHandler(AgentEventHandler): 
    """
    Handles LLMUserMessageReadyEvents by sending the prepared LLMUserMessage 
    to the LLM, emitting AGENT_DATA_ASSISTANT_CHUNK events via the notifier
    for each chunk, emitting AGENT_DATA_ASSISTANT_CHUNK_STREAM_END upon completion,
    and then enqueuing an LLMCompleteResponseReceivedEvent with the full aggregated response.
    """

    def __init__(self):
        logger.info("LLMUserMessageReadyEventHandler initialized.") 

    async def handle(self,
                     event: LLMUserMessageReadyEvent, 
                     context: 'AgentContext') -> None:
        if not isinstance(event, LLMUserMessageReadyEvent): 
            logger.warning(f"LLMUserMessageReadyEventHandler received non-LLMUserMessageReadyEvent: {type(event)}. Skipping.")
            return

        agent_id = context.agent_id 
        if context.state.llm_instance is None: 
            error_msg = f"Agent '{agent_id}' received LLMUserMessageReadyEvent but LLM instance is not yet initialized."
            logger.critical(error_msg)
            if context.phase_manager and context.phase_manager.notifier:
                context.phase_manager.notifier.notify_agent_error_output_generation( # USE RENAMED METHOD
                    error_source="LLMUserMessageReadyEventHandler.pre_llm_check",
                    error_message=error_msg
                )
            raise RuntimeError(error_msg) 

        llm_user_message: LLMUserMessage = event.llm_user_message
        logger.info(f"Agent '{agent_id}' handling LLMUserMessageReadyEvent: '{llm_user_message.content[:100]}...'") 
        logger.debug(f"Agent '{agent_id}' preparing to send full message to LLM:\n---\n{llm_user_message.content}\n---")
        
        context.state.add_message_to_history({"role": "user", "content": llm_user_message.content})

        complete_response_text = ""
        complete_reasoning_text = ""
        token_usage: Optional[TokenUsage] = None
        
        notifier: Optional['AgentExternalEventNotifier'] = None
        if context.phase_manager:
            notifier = context.phase_manager.notifier
        
        if not notifier: # pragma: no cover
            logger.error(f"Agent '{agent_id}': Notifier not available in LLMUserMessageReadyEventHandler. Cannot emit chunk events.")

        try:
            async for chunk_response in context.state.llm_instance.stream_user_message(llm_user_message):
                if not isinstance(chunk_response, ChunkResponse): 
                    logger.warning(f"Agent '{agent_id}' received unexpected chunk type: {type(chunk_response)} during LLM stream. Expected ChunkResponse.")
                    continue

                if chunk_response.content:
                    complete_response_text += chunk_response.content
                if chunk_response.reasoning:
                    complete_reasoning_text += chunk_response.reasoning

                if chunk_response.is_complete and chunk_response.usage:
                    token_usage = chunk_response.usage
                    logger.debug(f"Agent '{agent_id}' received final chunk with token usage: {token_usage}")

                if notifier:
                    try:
                        # The chunk object now contains both content and reasoning
                        notifier.notify_agent_data_assistant_chunk(chunk_response) 
                    except Exception as e_notify: 
                         logger.error(f"Agent '{agent_id}': Error notifying assistant chunk generated: {e_notify}", exc_info=True)
            
            if notifier:
                try:
                    notifier.notify_agent_data_assistant_chunk_stream_end() 
                except Exception as e_notify_end: 
                    logger.error(f"Agent '{agent_id}': Error notifying assistant chunk stream end: {e_notify_end}", exc_info=True)

            logger.debug(f"Agent '{agent_id}' LLM stream completed. Full response length: {len(complete_response_text)}. Reasoning length: {len(complete_reasoning_text)}. Chunk stream ended event emitted.")
            if complete_reasoning_text:
                logger.debug(f"Agent '{agent_id}' aggregated full LLM reasoning:\n---\n{complete_reasoning_text}\n---")
            logger.debug(f"Agent '{agent_id}' aggregated full LLM response:\n---\n{complete_response_text}\n---")

        except Exception as e:
            logger.error(f"Agent '{agent_id}' error during LLM stream: {e}", exc_info=True)
            error_message_for_output = f"Error processing your request with the LLM: {str(e)}"
            
            logger.warning(f"Agent '{agent_id}' LLM stream error. Error message for output: {error_message_for_output}")
            context.state.add_message_to_history({"role": "assistant", "content": error_message_for_output, "is_error": True})
            
            if notifier:
                try:
                    notifier.notify_agent_data_assistant_chunk_stream_end() 
                    notifier.notify_agent_error_output_generation( 
                        error_source="LLMUserMessageReadyEventHandler.stream_user_message",
                        error_message=error_message_for_output,
                        error_details=traceback.format_exc()
                    )
                except Exception as e_notify_err: 
                    logger.error(f"Agent '{agent_id}': Error notifying agent output error or chunk stream end after LLM stream failure: {e_notify_err}", exc_info=True)

            complete_response_on_error = CompleteResponse(content=error_message_for_output, usage=None)
            llm_complete_event_on_error = LLMCompleteResponseReceivedEvent(
                complete_response=complete_response_on_error,
                is_error=True 
            )
            await context.input_event_queues.enqueue_internal_system_event(llm_complete_event_on_error)
            logger.info(f"Agent '{agent_id}' enqueued LLMCompleteResponseReceivedEvent with error details from LLMUserMessageReadyEventHandler.")
            return 

        # Add message to history with reasoning
        history_entry = {"role": "assistant", "content": complete_response_text}
        if complete_reasoning_text:
            history_entry["reasoning"] = complete_reasoning_text
        context.state.add_message_to_history(history_entry)
        
        # Create complete response with reasoning
        complete_response_obj = CompleteResponse(
            content=complete_response_text,
            reasoning=complete_reasoning_text,
            usage=token_usage
        )
        llm_complete_event = LLMCompleteResponseReceivedEvent(
            complete_response=complete_response_obj
        )
        await context.input_event_queues.enqueue_internal_system_event(llm_complete_event)
        logger.info(f"Agent '{agent_id}' enqueued LLMCompleteResponseReceivedEvent from LLMUserMessageReadyEventHandler.")