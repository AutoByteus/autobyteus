# file: autobyteus/autobyteus/agent/input_processor/metadata_appending_input_processor.py
import logging
from typing import TYPE_CHECKING

from .base_user_input_processor import BaseAgentUserInputMessageProcessor # Relative import, OK

if TYPE_CHECKING:
    from autobyteus.agent.message.agent_input_user_message import AgentInputUserMessage
    from autobyteus.agent.context import AgentContext # MODIFIED IMPORT

logger = logging.getLogger(__name__)

class MetadataAppendingInputProcessor(BaseAgentUserInputMessageProcessor):
    """
    A processor that appends fixed metadata to the message.
    Example: Appends agent_id and definition_name to metadata.
    """
    async def process(self,
                      message: 'AgentInputUserMessage', 
                      context: 'AgentContext') -> 'AgentInputUserMessage': 
        logger.debug(f"Agent '{context.agent_id}': MetadataAppendingInputProcessor processing message.")
        message.metadata["processed_by_agent_id"] = context.agent_id
        message.metadata["processed_with_definition"] = context.definition.name
        logger.info(f"Agent '{context.agent_id}': Appended 'processed_by_agent_id' and 'processed_with_definition' to message metadata.")
        return message
