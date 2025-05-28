# file: autobyteus/autobyteus/agent/handlers/llm_user_message_ready_event_handler.py
import logging
import traceback
from typing import TYPE_CHECKING, cast

from autobyteus.agent.handlers.base_event_handler import AgentEventHandler
from autobyteus.agent.events import LLMUserMessageReadyEvent, LLMCompleteResponseReceivedEvent # RENAMED Event
from autobyteus.agent.events import END_OF_STREAM_SENTINEL
from autobyteus.llm.user_message import LLMUserMessage
from autobyteus.llm.utils.response_types import ChunkResponse, CompleteResponse

if TYPE_CHECKING:
    from autobyteus.agent.context import AgentContext

logger = logging.getLogger(__name__)

class LLMUserMessageReadyEventHandler(AgentEventHandler): # RENAMED Class
    """
    Handles LLMUserMessageReadyEvents by sending the prepared LLMUserMessage 
    (derived from user or inter-agent input) to the LLM,
    streaming the ChunkResponse objects to `assistant_output_chunk_queue`, and then
    enqueuing an LLMCompleteResponseReceivedEvent with the full aggregated response.
    """

    def __init__(self):
        logger.info("LLMUserMessageReadyEventHandler initialized.") # RENAMED Class in log

    async def handle(self,
                     event: LLMUserMessageReadyEvent, # RENAMED Event type
                     context: 'AgentContext') -> None:
        if not isinstance(event, LLMUserMessageReadyEvent): # RENAMED Event type check
            logger.warning(f"LLMUserMessageReadyEventHandler received non-LLMUserMessageReadyEvent: {type(event)}. Skipping.")
            return

        # Safeguard: Ensure LLM is initialized.
        if context.state.llm_instance is None: # Access via context.state
            error_msg = f"Agent '{context.agent_id}' received LLMUserMessageReadyEvent but LLM instance is not yet initialized. This indicates a potential issue in the agent's state or event flow."
            logger.critical(error_msg)
            raise RuntimeError(error_msg)

        llm_user_message: LLMUserMessage = event.llm_user_message
        logger.info(f"Agent '{context.agent_id}' handling LLMUserMessageReadyEvent: '{llm_user_message.content[:100]}...'") 
        logger.debug(f"Agent '{context.agent_id}' preparing to send full message to LLM:\n---\n{llm_user_message.content}\n---")
        
        # Access conversation_history and queues via context.state
        context.state.add_message_to_history({"role": "user", "content": llm_user_message.content})

        complete_response_text = ""
        chunk_queue = context.state.queues.assistant_output_chunk_queue
        try:
            # Access llm_instance via context.state
            async for chunk_response in context.state.llm_instance.stream_user_message(llm_user_message):
                if not isinstance(chunk_response, ChunkResponse):
                    logger.warning(f"Agent '{context.agent_id}' received unexpected chunk type: {type(chunk_response)} during LLM stream. Expected ChunkResponse.")
                    continue

                complete_response_text += chunk_response.content
                await chunk_queue.put(chunk_response)
            
            await chunk_queue.put(END_OF_STREAM_SENTINEL)
            logger.debug(f"Agent '{context.agent_id}' LLM stream completed. Full response length: {len(complete_response_text)}. Sentinel placed in chunk queue.")
            logger.debug(f"Agent '{context.agent_id}' aggregated full LLM response:\n---\n{complete_response_text}\n---")

        except Exception as e:
            logger.error(f"Agent '{context.agent_id}' error during LLM stream: {e}", exc_info=True)
            error_message_for_output = f"Error processing your request with the LLM: {str(e)}"
            
            logger.warning(f"Agent '{context.agent_id}' LLM stream error. Error message for output: {error_message_for_output}")
            context.state.add_message_to_history({"role": "assistant", "content": error_message_for_output, "is_error": True})
            
            if not chunk_queue.full(): 
                await chunk_queue.put(END_OF_STREAM_SENTINEL)
            else:
                logger.warning(f"Agent '{context.agent_id}' chunk_queue is full, cannot place error sentinel.")

            llm_complete_event_on_error = LLMCompleteResponseReceivedEvent(
                complete_response_text=error_message_for_output, 
                is_error=True 
            )
            await context.state.queues.enqueue_internal_system_event(llm_complete_event_on_error)
            logger.info(f"Agent '{context.agent_id}' enqueued LLMCompleteResponseReceivedEvent with error details from LLMUserMessageReadyEventHandler.")
            return 

        context.state.add_message_to_history({"role": "assistant", "content": complete_response_text})
        
        llm_complete_event = LLMCompleteResponseReceivedEvent(
            complete_response_text=complete_response_text
        )
        await context.state.queues.enqueue_internal_system_event(llm_complete_event)
        logger.info(f"Agent '{context.agent_id}' enqueued LLMCompleteResponseReceivedEvent from LLMUserMessageReadyEventHandler.")

