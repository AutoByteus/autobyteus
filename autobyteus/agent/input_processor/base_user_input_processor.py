# file: autobyteus/autobyteus/agent/input_processor/base_user_input_processor.py
import logging
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from .processor_meta import AgentUserInputMessageProcessorMeta # Relative import, OK

if TYPE_CHECKING:
    from autobyteus.agent.message.agent_input_user_message import AgentInputUserMessage 
    from autobyteus.agent.context import AgentContext # MODIFIED IMPORT

logger = logging.getLogger(__name__)

class BaseAgentUserInputMessageProcessor(ABC, metaclass=AgentUserInputMessageProcessorMeta):
    """
    Abstract base class for agent user input message processors.
    These processors can modify an AgentInputUserMessage, specifically from a user,
    before it is converted to an LLMUserMessage.
    Concrete subclasses are auto-registered using AgentUserInputMessageProcessorMeta.
    """

    @classmethod
    def get_name(cls) -> str:
        """
        Returns the unique registration name for this processor.
        Defaults to the class name. Can be overridden by subclasses.
        """
        return cls.__name__

    @abstractmethod
    async def process(self,
                      message: 'AgentInputUserMessage', 
                      context: 'AgentContext') -> 'AgentInputUserMessage': 
        """
        Processes the given AgentInputUserMessage.

        Args:
            message: The AgentInputUserMessage to process.
            context: The AgentContext, providing access to the agent's state,
                     definition, etc.

        Returns:
            The processed (potentially modified) AgentInputUserMessage.

        Raises:
            NotImplementedError: If the subclass does not implement this method.
        """
        raise NotImplementedError("Subclasses must implement the 'process' method.")

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}>"
