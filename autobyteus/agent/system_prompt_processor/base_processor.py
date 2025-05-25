# file: autobyteus/autobyteus/agent/system_prompt_processor/base_processor.py
import logging
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Dict

from .processor_meta import SystemPromptProcessorMeta # Relative import

if TYPE_CHECKING:
    from autobyteus.tools.base_tool import BaseTool
    # AgentDefinition might be needed if processors need more context from definition
    # from autobyteus.agent.registry.agent_definition import AgentDefinition 

logger = logging.getLogger(__name__)

class BaseSystemPromptProcessor(ABC, metaclass=SystemPromptProcessorMeta):
    """
    Abstract base class for system prompt processors.
    These processors can modify an agent's system prompt string before it's
    used by the LLM, for example, to inject dynamic information like tool descriptions.
    Concrete subclasses are auto-registered using SystemPromptProcessorMeta.
    """

    @classmethod
    def get_name(cls) -> str:
        """
        Returns the unique registration name for this processor.
        Defaults to the class name. Can be overridden by subclasses for a more
        stable or user-friendly name.
        """
        return cls.__name__

    @abstractmethod
    def process(self,
                system_prompt: str,
                tool_instances: Dict[str, 'BaseTool'],
                agent_id: str) -> str:
        """
        Processes the given system prompt string.

        Args:
            system_prompt: The current system prompt string to process.
            tool_instances: A dictionary of instantiated tools available to the agent,
                            keyed by tool name. Processors can use this to extract
                            tool information (e.g., descriptions, schemas).
            agent_id: The ID of the agent for whom the prompt is being processed,
                      useful for logging or context-specific behavior.

        Returns:
            The processed (potentially modified) system prompt string.

        Raises:
            NotImplementedError: If the subclass does not implement this method.
        """
        raise NotImplementedError("Subclasses must implement the 'process' method.")

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}>"
