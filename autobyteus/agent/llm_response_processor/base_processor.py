# file: autobyteus/autobyteus/agent/llm_response_processor/base_processor.py
import logging
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from .processor_meta import LLMResponseProcessorMeta # Relative import, OK

if TYPE_CHECKING:
    from autobyteus.agent.context import AgentContext # MODIFIED IMPORT

logger = logging.getLogger(__name__)

class BaseLLMResponseProcessor(ABC, metaclass=LLMResponseProcessorMeta):
    """
    Abstract base class for LLM response processors.
    These processors analyze the LLM's textual response. If they identify a specific
    actionable item (like a tool invocation), they are responsible for enqueuing
    the appropriate event into the agent's context and indicating success.
    Concrete subclasses are auto-registered.
    """

    @classmethod
    def get_name(cls) -> str:
        """
        Returns the unique registration name for this processor.
        Defaults to the class name. Should be overridden by subclasses
        to provide a stable, user-friendly name (e.g., "xml_tool_usage").
        """
        return cls.__name__

    @abstractmethod
    async def process_response(self, response: str, context: 'AgentContext') -> bool:
        """
        Processes the LLM's response string. If an actionable item is found (e.g.,
        a tool invocation), this method should enqueue the corresponding event
        (e.g., PendingToolInvocationEvent) into the context's queues and return True.

        Args:
            response: The textual response from the LLM.
            context: The agent's context, providing access to queues and other state.

        Returns:
            True if the processor successfully identified an action and enqueued an
            event, False otherwise.
        """
        raise NotImplementedError("Subclasses must implement the 'process_response' method.")

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}>"
