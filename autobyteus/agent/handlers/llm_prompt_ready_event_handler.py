# file: autobyteus/autobyteus/agent/handlers/llm_prompt_ready_event_handler.py
import logging
import traceback
from typing import TYPE_CHECKING, cast

from autobyteus.agent.handlers.base_event_handler import AgentEventHandler
from autobyteus.agent.events import LLMPromptReadyEvent, LLMCompleteResponseReceivedEvent # MODIFIED IMPORT
from autobyteus.agent.events import END_OF_STREAM_SENTINEL
from autobyteus.llm.user_message import LLMUserMessage # MODIFIED IMPORT
from autobyteus.llm.utils.response_types import ChunkResponse, CompleteResponse

if TYPE_CHECKING:
    from autobyteus.agent.context import AgentContext # MODIFIED IMPORT

logger = logging.getLogger(__name__)

class LLMPromptReadyEventHandler(AgentEventHandler):
    """
    Handles LLMPromptReadyEvents by sending the prepared LLMUserMessage to the LLM,
    streaming the ChunkResponse objects to `assistant_output_chunk_queue`, and then
    enqueuing an LLMCompleteResponseReceivedEvent with the full aggregated response.
    """

    def __init__(self):
        logger.info("LLMPromptReadyEventHandler initialized.")

    async def handle(self,
                     event: LLMPromptReadyEvent, 
                     context: 'AgentContext') -> None:
        llm_user_message: LLMUserMessage = event.llm_user_message
        logger.info(f"Agent '{context.agent_id}' handling LLMPromptReadyEvent: '{llm_user_message.content[:100]}...'") 
        
        context.add_message_to_history({"role": "user", "content": llm_user_message.content})

        complete_response_text = ""
        chunk_queue = context.queues.assistant_output_chunk_queue
        try:
            async for chunk_response in context.llm_instance.stream_user_message(llm_user_message):
                if not isinstance(chunk_response, ChunkResponse):
                    logger.warning(f"Agent '{context.agent_id}' received unexpected chunk type: {type(chunk_response)} during LLM stream. Expected ChunkResponse.")
                    continue

                complete_response_text += chunk_response.content
                await chunk_queue.put(chunk_response)
            
            await chunk_queue.put(END_OF_STREAM_SENTINEL)
            logger.debug(f"Agent '{context.agent_id}' LLM stream completed. Full response length: {len(complete_response_text)}. Sentinel placed in chunk queue.")

        except Exception as e:
            logger.error(f"Agent '{context.agent_id}' error during LLM stream: {e}", exc_info=True)
            error_message_for_output = f"Error processing your request with the LLM: {str(e)}"
            
            context.add_message_to_history({"role": "assistant", "content": error_message_for_output, "is_error": True})
            
            if not chunk_queue.full(): 
                await chunk_queue.put(END_OF_STREAM_SENTINEL)
            else:
                logger.warning(f"Agent '{context.agent_id}' chunk_queue is full, cannot place error sentinel.")

            llm_complete_event_on_error = LLMCompleteResponseReceivedEvent(
                complete_response_text=error_message_for_output, 
                is_error=True 
            )
            await context.queues.enqueue_internal_system_event(llm_complete_event_on_error)
            logger.info(f"Agent '{context.agent_id}' enqueued LLMCompleteResponseReceivedEvent with error details from LLMPromptReadyEventHandler.")
            return 

        context.add_message_to_history({"role": "assistant", "content": complete_response_text})
        
        llm_complete_event = LLMCompleteResponseReceivedEvent(
            complete_response_text=complete_response_text
        )
        await context.queues.enqueue_internal_system_event(llm_complete_event)
        logger.info(f"Agent '{context.agent_id}' enqueued LLMCompleteResponseReceivedEvent from LLMPromptReadyEventHandler.")
