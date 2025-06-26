# file: autobyteus/autobyteus/agent/bootstrap_steps/base_bootstrap_step.py
import logging
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from autobyteus.agent.context import AgentContext
    from autobyteus.agent.phases import AgentPhaseManager

logger = logging.getLogger(__name__)

class BaseBootstrapStep(ABC):
    """
    Abstract base class for individual steps in the agent bootstrapping process.
    Each step is responsible for a specific part of the initialization and
    for reporting its success or failure.
    """

    @abstractmethod
    async def execute(self,
                      context: 'AgentContext',
                      phase_manager: 'AgentPhaseManager') -> bool:
        """
        Executes the bootstrap step.

        Args:
            context: The agent's context, providing access to configuration and state.
            phase_manager: The agent's phase manager for notifying phase transitions.

        Returns:
            True if the step completed successfully, False otherwise.
            If False, the step is expected to have handled logging and enqueuing
            an AgentErrorEvent.
        """
        raise NotImplementedError("Subclasses must implement the 'execute' method.")

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}>"
