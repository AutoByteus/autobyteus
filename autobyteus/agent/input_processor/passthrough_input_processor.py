# file: autobyteus/autobyteus/agent/input_processor/passthrough_input_processor.py
import logging
from typing import TYPE_CHECKING

from .base_user_input_processor import BaseAgentUserInputMessageProcessor 

if TYPE_CHECKING:
    from autobyteus.agent.message.agent_input_user_message import AgentInputUserMessage
    from autobyteus.agent.context import AgentContext # Composite AgentContext
    from autobyteus.agent.events import UserMessageReceivedEvent

logger = logging.getLogger(__name__)

class PassthroughInputProcessor(BaseAgentUserInputMessageProcessor):
    """
    A processor that returns the message unchanged.
    Can be used as a default or for testing.
    """
    @classmethod
    def get_name(cls) -> str:
        return "PassthroughInputProcessor"

    async def process(self,
                      message: 'AgentInputUserMessage', 
                      context: 'AgentContext',
                      triggering_event: 'UserMessageReceivedEvent') -> 'AgentInputUserMessage':
        """
        Handles the message by returning it without modification.
        The 'triggering_event' parameter is ignored by this processor.
        """
        agent_id = context.agent_id # Convenience property
        logger.debug(f"Agent '{agent_id}': PassthroughInputProcessor received message, returning as is.")
        return message
