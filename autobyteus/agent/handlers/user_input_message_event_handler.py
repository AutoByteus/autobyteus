# file: autobyteus/autobyteus/agent/handlers/user_input_message_event_handler.py
import logging
from typing import TYPE_CHECKING

from autobyteus.agent.handlers.base_event_handler import AgentEventHandler
from autobyteus.agent.events import UserMessageReceivedEvent, LLMUserMessageReadyEvent 
from autobyteus.agent.message.agent_input_user_message import AgentInputUserMessage 
from autobyteus.agent.input_processor import default_input_processor_registry
from autobyteus.llm.user_message import LLMUserMessage


if TYPE_CHECKING:
    from autobyteus.agent.context import AgentContext 
    from autobyteus.agent.input_processor.base_user_input_processor import BaseAgentUserInputMessageProcessor


logger = logging.getLogger(__name__)

class UserInputMessageEventHandler(AgentEventHandler):
    """
    Handles UserMessageReceivedEvents by first applying any configured
    AgentUserInputMessageProcessors (looked up via registry) to the AgentInputUserMessage,
    then converting the processed message into an LLMUserMessage, and finally
    enqueuing an LLMUserMessageReadyEvent for further processing by the LLM.
    """

    def __init__(self):
        logger.info("UserInputMessageEventHandler initialized.")
        self.input_processor_registry = default_input_processor_registry


    async def handle(self,
                     event: UserMessageReceivedEvent, 
                     context: 'AgentContext') -> None:
        if not isinstance(event, UserMessageReceivedEvent): 
            logger.warning(f"UserInputMessageEventHandler received non-UserMessageReceivedEvent: {type(event)}. Skipping.")
            return

        original_agent_input_user_msg: AgentInputUserMessage = event.agent_input_user_message 
        processed_agent_input_user_msg: AgentInputUserMessage = original_agent_input_user_msg 
        
        logger.info(f"Agent '{context.agent_id}' handling UserMessageReceivedEvent: '{original_agent_input_user_msg.content[:100]}...'") 
        
        processor_names = context.config.definition.input_processor_names
        if processor_names:
            logger.debug(f"Agent '{context.agent_id}': Applying input processors by name: {processor_names}")
            for processor_name in processor_names:
                processor_definition = self.input_processor_registry.get_processor_definition(processor_name)
                
                if processor_definition:
                    processor_class = processor_definition.processor_class
                    processor_instance: 'BaseAgentUserInputMessageProcessor' = processor_class()
                    try:
                        logger.debug(f"Agent '{context.agent_id}': Applying input processor '{processor_name}' (class: {processor_class.__name__}).")
                        msg_before_this_processor = processed_agent_input_user_msg 
                        processed_agent_input_user_msg = await processor_instance.process(msg_before_this_processor, context)
                        logger.info(f"Agent '{context.agent_id}': Input processor '{processor_name}' applied successfully.")
                    except Exception as e:
                        logger.error(f"Agent '{context.agent_id}': Error applying input processor '{processor_name}': {e}. "
                                     f"Skipping this processor and continuing with message from before this processor.", exc_info=True)
                        processed_agent_input_user_msg = msg_before_this_processor 
                else:
                    logger.warning(f"Agent '{context.agent_id}': Input processor name '{processor_name}' not found in registry. Skipping.")
        else:
            logger.debug(f"Agent '{context.agent_id}': No input processors configured in agent definition.")

        llm_user_message = LLMUserMessage( 
            content=processed_agent_input_user_msg.content,
            image_urls=processed_agent_input_user_msg.image_urls 
        )
        
        llm_user_message_ready_event = LLMUserMessageReadyEvent(llm_user_message=llm_user_message) 
        await context.input_event_queues.enqueue_internal_system_event(llm_user_message_ready_event)
        
        logger.info(f"Agent '{context.agent_id}' processed AgentInputUserMessage (processors: {processor_names}) and enqueued LLMUserMessageReadyEvent.")
