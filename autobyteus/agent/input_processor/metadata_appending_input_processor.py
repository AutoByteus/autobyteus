# file: autobyteus/autobyteus/agent/input_processor/metadata_appending_input_processor.py
import logging
from typing import TYPE_CHECKING

from .base_user_input_processor import BaseAgentUserInputMessageProcessor 

if TYPE_CHECKING:
    from autobyteus.agent.message.agent_input_user_message import AgentInputUserMessage
    from autobyteus.agent.context import AgentContext # Composite AgentContext
    from autobyteus.agent.events import UserMessageReceivedEvent

logger = logging.getLogger(__name__)

class MetadataAppendingInputProcessor(BaseAgentUserInputMessageProcessor):
    """
    A processor that appends fixed metadata to the message.
    Example: Appends agent_id and config_name to metadata.
    """
    async def process(self,
                      message: 'AgentInputUserMessage', 
                      context: 'AgentContext',
                      triggering_event: 'UserMessageReceivedEvent') -> 'AgentInputUserMessage':
        """
        Handles the message by appending metadata.
        The 'triggering_event' parameter is ignored by this processor.
        """
        agent_id = context.agent_id
        config_name = context.config.name

        logger.debug(f"Agent '{agent_id}': MetadataAppendingInputProcessor processing message.")
        message.metadata["processed_by_agent_id"] = agent_id
        message.metadata["processed_with_config_name"] = config_name
        logger.info(f"Agent '{agent_id}': Appended 'processed_by_agent_id' and 'processed_with_config_name' to message metadata.")
        return message
