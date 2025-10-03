# file: autobyteus/autobyteus/agent/handlers/user_input_message_event_handler.py
import logging
import copy
from typing import TYPE_CHECKING

from autobyteus.agent.handlers.base_event_handler import AgentEventHandler
from autobyteus.agent.events import UserMessageReceivedEvent, LLMUserMessageReadyEvent
from autobyteus.agent.message.agent_input_user_message import AgentInputUserMessage
from autobyteus.agent.input_processor import BaseAgentUserInputMessageProcessor
from autobyteus.agent.message.multimodal_message_builder import build_llm_user_message
from autobyteus.agent.sender_type import SenderType


if TYPE_CHECKING:
    from autobyteus.agent.context import AgentContext
    from autobyteus.agent.events.notifiers import AgentExternalEventNotifier

logger = logging.getLogger(__name__)

class UserInputMessageEventHandler(AgentEventHandler):
    """
    Handles UserMessageReceivedEvents by first applying any configured
    AgentUserInputMessageProcessors, then using the multimodal_message_builder
    to convert the processed message into an LLMUserMessage, and finally
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

        # --- UPDATED LOGIC: Check sender_type for system-generated tasks and notify TUI ---
        if original_agent_input_user_msg.sender_type == SenderType.SYSTEM:
            if context.phase_manager:
                notifier: 'AgentExternalEventNotifier' = context.phase_manager.notifier
                notification_data = {
                    "sender_id": original_agent_input_user_msg.metadata.get("sender_id", "system"),
                    "content": original_agent_input_user_msg.content,
                }
                notifier.notify_agent_data_system_task_notification_received(notification_data)
                logger.info(f"Agent '{context.agent_id}' emitted system task notification for TUI based on SYSTEM sender_type.")
        # --- END UPDATED LOGIC ---

        # Create a deep copy of the message to pass through the processor chain.
        # This prevents in-place mutation of the original event's message object,
        # ensuring that processors like UserInputPersistenceProcessor can access
        # the true original content via the triggering_event.
        processed_agent_input_user_msg = copy.deepcopy(original_agent_input_user_msg)

        logger.info(f"Agent '{context.agent_id}' handling UserMessageReceivedEvent (type: {original_agent_input_user_msg.sender_type.value}): '{original_agent_input_user_msg.content}'")

        processor_instances = context.config.input_processors
        if processor_instances:
            # Sort processors by their order attribute
            sorted_processors = sorted(processor_instances, key=lambda p: p.get_order())
            processor_names = [p.get_name() for p in sorted_processors]
            logger.debug(f"Agent '{context.agent_id}': Applying input processors in order: {processor_names}")
            
            for processor_instance in sorted_processors:
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

        # --- Refactored: Use the dedicated builder ---
        llm_user_message = build_llm_user_message(processed_agent_input_user_msg)
        
        llm_user_message_ready_event = LLMUserMessageReadyEvent(llm_user_message=llm_user_message)
        await context.input_event_queues.enqueue_internal_system_event(llm_user_message_ready_event)

        logger.info(f"Agent '{context.agent_id}' processed AgentInputUserMessage and enqueued LLMUserMessageReadyEvent.")
