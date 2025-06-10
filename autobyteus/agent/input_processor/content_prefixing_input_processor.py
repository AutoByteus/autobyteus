# file: autobyteus/autobyteus/agent/input_processor/content_prefixing_input_processor.py
import logging
from typing import TYPE_CHECKING

from .base_user_input_processor import BaseAgentUserInputMessageProcessor 

if TYPE_CHECKING:
    from autobyteus.agent.message.agent_input_user_message import AgentInputUserMessage
    from autobyteus.agent.context import AgentContext # Composite AgentContext
    from autobyteus.agent.events import UserMessageReceivedEvent

logger = logging.getLogger(__name__)

class ContentPrefixingInputProcessor(BaseAgentUserInputMessageProcessor):
    """
    A processor that adds a predefined prefix to the message content.
    The prefix is defined by the agent's custom_data (in AgentRuntimeState) or a default.
    Example prefix key in custom_data: "content_prefix"
    """
    DEFAULT_PREFIX = "[Processed Message] "

    async def process(self,
                      message: 'AgentInputUserMessage', 
                      context: 'AgentContext',
                      triggering_event: 'UserMessageReceivedEvent') -> 'AgentInputUserMessage':
        """
        Handles the message by prefixing its content.
        The 'triggering_event' parameter is ignored by this processor.
        """
        agent_id = context.agent_id # Convenience property
        logger.debug(f"Agent '{agent_id}': ContentPrefixingInputProcessor processing message.")
        
        # Access custom_data via convenience property (or context.state.custom_data)
        prefix = context.custom_data.get("content_prefix", self.DEFAULT_PREFIX)
        if not isinstance(prefix, str):
            logger.warning(f"Agent '{agent_id}': 'content_prefix' in custom_data is not a string. Using default prefix. Found: {type(prefix)}")
            prefix = self.DEFAULT_PREFIX
            
        message.content = prefix + message.content
        logger.info(f"Agent '{agent_id}': Prefixed message content with '{prefix}'.")
        return message
