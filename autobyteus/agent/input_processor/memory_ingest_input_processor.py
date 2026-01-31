import logging
from typing import TYPE_CHECKING

from autobyteus.agent.input_processor.base_user_input_processor import BaseAgentUserInputMessageProcessor
from autobyteus.agent.message.multimodal_message_builder import build_llm_user_message

if TYPE_CHECKING:
    from autobyteus.agent.message.agent_input_user_message import AgentInputUserMessage
    from autobyteus.agent.context import AgentContext
    from autobyteus.agent.events import UserMessageReceivedEvent

logger = logging.getLogger(__name__)


class MemoryIngestInputProcessor(BaseAgentUserInputMessageProcessor):
    @classmethod
    def get_order(cls) -> int:
        return 900

    async def process(
        self,
        message: "AgentInputUserMessage",
        context: "AgentContext",
        triggering_event: "UserMessageReceivedEvent",
    ) -> "AgentInputUserMessage":
        memory_manager = getattr(context.state, "memory_manager", None)
        if not memory_manager:
            return message

        turn_id = memory_manager.start_turn()
        context.state.active_turn_id = turn_id

        llm_user_message = build_llm_user_message(message)
        memory_manager.ingest_user_message(
            llm_user_message,
            turn_id=turn_id,
            source_event="LLMUserMessageReadyEvent",
        )
        logger.debug("MemoryIngestInputProcessor stored processed user input with turn_id %s", turn_id)
        return message
