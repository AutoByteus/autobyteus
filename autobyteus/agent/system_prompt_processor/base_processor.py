# file: autobyteus/autobyteus/agent/system_prompt_processor/base_processor.py
import logging
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Dict

from .processor_meta import SystemPromptProcessorMeta

if TYPE_CHECKING:
    from autobyteus.tools.base_tool import BaseTool
    from autobyteus.agent.context import AgentContext

logger = logging.getLogger(__name__)

class BaseSystemPromptProcessor(ABC, metaclass=SystemPromptProcessorMeta):
    """
    Abstract base class for system prompt processors.
    Subclasses should be instantiated and passed to the AgentSpecification.
    """
    @classmethod
    def get_name(cls) -> str:
        """
        Returns the unique name for this processor.
        Defaults to the class name. Can be overridden by subclasses.
        """
        return cls.__name__

    @abstractmethod
    def process(self,
                system_prompt: str,
                tool_instances: Dict[str, 'BaseTool'],
                agent_id: str,
                context: 'AgentContext') -> str:
        """
        Processes the given system prompt string.

        Args:
            system_prompt: The current system prompt string to process.
            tool_instances: A dictionary of instantiated tools available to the agent.
            agent_id: The ID of the agent for whom the prompt is being processed.
            context: The agent's context, providing access to agent spec, state, and config.

        Returns:
            The processed (potentially modified) system prompt string.
        """
        raise NotImplementedError("Subclasses must implement the 'process' method.")

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}>"
