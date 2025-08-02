# file: autobyteus/autobyteus/agent_team/handlers/base_agent_team_event_handler.py
import logging
from abc import ABC, abstractmethod
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from autobyteus.agent_team.context.agent_team_context import AgentTeamContext

logger = logging.getLogger(__name__)

class BaseAgentTeamEventHandler(ABC):
    """Abstract base class for agent team event handlers."""

    @abstractmethod
    async def handle(self, event: Any, context: 'AgentTeamContext') -> None:
        raise NotImplementedError("Subclasses must implement the 'handle' method.")
