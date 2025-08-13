# file: autobyteus/autobyteus/agent_team/shutdown_steps/base_agent_team_shutdown_step.py
import logging
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from autobyteus.agent_team.context.agent_team_context import AgentTeamContext

logger = logging.getLogger(__name__)

class BaseAgentTeamShutdownStep(ABC):
    """Abstract base class for individual steps in the agent team shutdown process."""
    @abstractmethod
    async def execute(self, context: 'AgentTeamContext') -> bool:
        """Executes the shutdown step."""
        raise NotImplementedError("Subclasses must implement the 'execute' method.")
