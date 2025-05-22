# file: autobyteus/autobyteus/agent/input_processor/passthrough_input_processor.py
import logging
from typing import TYPE_CHECKING

from .base_user_input_processor import BaseAgentUserInputMessageProcessor # Relative import, OK

if TYPE_CHECKING:
    # This import was incorrect in the original context, should be AgentInputUserMessage
    from autobyteus.agent.message.agent_input_user_message import AgentInputUserMessage
    from autobyteus.agent.context import AgentContext # MODIFIED IMPORT

logger = logging.getLogger(__name__)

class PassthroughInputProcessor(BaseAgentUserInputMessageProcessor):
    """
    A processor that returns the message unchanged.
    Can be used as a default or for testing.
    """
    async def process(self,
                      message: 'AgentInputUserMessage', 
                      context: 'AgentContext') -> 'AgentInputUserMessage': 
        logger.debug(f"Agent '{context.agent_id}': PassthroughInputProcessor received message, returning as is.")
        return message
