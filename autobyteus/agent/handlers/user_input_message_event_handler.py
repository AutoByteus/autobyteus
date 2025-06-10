# file: autobyteus/autobyteus/agent/handlers/user_input_message_event_handler.py
import logging
from typing import TYPE_CHECKING

from autobyteus.agent.handlers.base_event_handler import AgentEventHandler
from autobyteus.agent.events import UserMessageReceivedEvent, LLMUserMessageReadyEvent 
from autobyteus.agent.message.agent_input_user_message import AgentInputUserMessage 
from autobyteus.agent.input_processor import BaseAgentUserInputMessageProcessor
from autobyteus.llm.user_message import LLMUserMessage


if TYPE_CHECKING:
    from autobyteus.agent.context import AgentContext 

logger = logging.getLogger(__name__)

class UserInputMessageEventHandler(AgentEventHandler):
    """
    Handles UserMessageReceivedEvents by first applying any configured
    AgentUserInputMessageProcessors (provided as instances) to the AgentInputUserMessage,
    then converting the processed message into an LLMUserMessage, and finally
    enqueuing an LLMUserMessageReadyEvent for further processing by the LLM.
    """

    def __init__(self):
        logger.info("UserInputMessageEventHandler initialized.")

    async def handle(self,
                     event: UserMessageReceivedEvent, 
                     context: 'AgentContext') -> None:
        if not isinstance(event, UserMessageReceivedEvent): 
            logger.warning(f"UserInputMessageEventHandler received non-UserMessageReceivedEvent: {type(event)}. Skipping.")
            return

        original_agent_input_user_msg: AgentInputUserMessage = event.agent_input_user_message 
        processed_agent_input_user_msg: AgentInputUserMessage = original_agent_input_user_msg 
        
        logger.info(f"Agent '{context.agent_id}' handling UserMessageReceivedEvent: '{original_agent_input_user_msg.content[:100]}...'") 
        
        processor_instances = context.config.input_processors
        if processor_instances:
            processor_names = [p.get_name() for p in processor_instances]
            logger.debug(f"Agent '{context.agent_id}': Applying input processors: {processor_names}")
            for processor_instance in processor_instances:
                processor_name_for_log = "unknown"
                try:
                    if not isinstance(processor_instance, BaseAgentUserInputMessageProcessor):
                        logger.error(f"Agent '{context.agent_id}': Invalid input processor type in config: {type(processor_instance)}. Skipping.")
                        continue
                    
                    processor_name_for_log = processor_instance.get_name()
                    logger.debug(f"Agent '{context.agent_id}': Applying input processor '{processor_name_for_log}'.")
                    msg_before_this_processor = processed_agent_input_user_msg
                    # Pass the original event to the processor
                    processed_agent_input_user_msg = await processor_instance.process(
                        message=msg_before_this_processor, 
                        context=context, 
                        triggering_event=event
                    )
                    logger.info(f"Agent '{context.agent_id}': Input processor '{processor_name_for_log}' applied successfully.")

                except Exception as e:
                    logger.error(f"Agent '{context.agent_id}': Error applying input processor '{processor_name_for_log}': {e}. "
                                 f"Skipping this processor and continuing with message from before this processor.", exc_info=True)
                    processed_agent_input_user_msg = msg_before_this_processor
        else:
            logger.debug(f"Agent '{context.agent_id}': No input processors configured in agent config.")

        llm_user_message = LLMUserMessage( 
            content=processed_agent_input_user_msg.content,
            image_urls=processed_agent_input_user_msg.image_urls 
        )
        
        llm_user_message_ready_event = LLMUserMessageReadyEvent(llm_user_message=llm_user_message) 
        await context.input_event_queues.enqueue_internal_system_event(llm_user_message_ready_event)
        
        logger.info(f"Agent '{context.agent_id}' processed AgentInputUserMessage and enqueued LLMUserMessageReadyEvent.")
