# file: autobyteus/autobyteus/agent/shutdown_steps/base_shutdown_step.py
import logging
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from autobyteus.agent.context import AgentContext

logger = logging.getLogger(__name__)

class BaseShutdownStep(ABC):
    """
    Abstract base class for individual steps in the agent shutdown process.
    Each step is responsible for a specific part of the cleanup and
    for reporting its success or failure.
    """

    @abstractmethod
    async def execute(self, context: 'AgentContext') -> bool:
        """
        Executes the shutdown step.

        Args:
            context: The agent's context, providing access to state and resources.

        Returns:
            True if the step completed successfully, False otherwise.
            If False, the step is expected to have handled its own detailed logging.
        """
        raise NotImplementedError("Subclasses must implement the 'execute' method.")

    def __repr__(self) -> str:
        return f"&lt;{self.__class__.__name__}&gt;"
