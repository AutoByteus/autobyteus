# file: autobyteus/autobyteus/agent_team/bootstrap_steps/base_agent_team_bootstrap_step.py
import logging
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from autobyteus.agent_team.context.agent_team_context import AgentTeamContext
    from autobyteus.agent_team.phases.agent_team_phase_manager import AgentTeamPhaseManager

logger = logging.getLogger(__name__)

class BaseAgentTeamBootstrapStep(ABC):
    """Abstract base class for individual steps in the agent team bootstrapping process."""

    @abstractmethod
    async def execute(self, context: 'AgentTeamContext', phase_manager: 'AgentTeamPhaseManager') -> bool:
        """
        Executes the bootstrap step.

        Returns:
            True if the step completed successfully, False otherwise.
        """
        raise NotImplementedError("Subclasses must implement the 'execute' method.")
