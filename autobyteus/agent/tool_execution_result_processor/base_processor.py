# file: autobyteus/autobyteus/agent/tool_execution_result_processor/base_processor.py
import logging
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from .processor_meta import ToolExecutionResultProcessorMeta

if TYPE_CHECKING:
    from autobyteus.agent.context import AgentContext
    from autobyteus.agent.events import ToolResultEvent

logger = logging.getLogger(__name__)

class BaseToolExecutionResultProcessor(ABC, metaclass=ToolExecutionResultProcessorMeta):
    """
    Abstract base class for processors that can modify a tool's execution result.
    These processors are applied after a tool runs but before its result is formatted
    for the LLM.
    """

    @classmethod
    def get_name(cls) -> str:
        """
        Returns the unique registration name for this processor.
        Defaults to the class name.
        """
        return cls.__name__

    @abstractmethod
    async def process(self,
                      event: 'ToolResultEvent',
                      context: 'AgentContext') -> 'ToolResultEvent':
        """
        Processes the given ToolResultEvent.

        Args:
            event: The ToolResultEvent containing the tool's output or error.
            context: The agent's context, providing access to config and state.

        Returns:
            The processed (potentially modified) ToolResultEvent.
        """
        raise NotImplementedError("Subclasses must implement the 'process' method.")

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}>"
