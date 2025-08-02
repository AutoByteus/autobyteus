# file: autobyteus/autobyteus/agent_team/base_agent_team.py
import logging
from abc import ABC, abstractmethod
from typing import Optional, Any, TYPE_CHECKING

# These are forward declarations that might be used by subclasses.
if TYPE_CHECKING:
    from autobyteus.agent_team.agent_team import AgentTeam

logger = logging.getLogger(__name__)

class BaseAgentTeam(ABC):
    """
    Optional abstract base class for creating domain-specific, type-safe
    APIs for agent teams.

    Users can subclass BaseAgentTeam to create a more structured and
    specific interface for their multi-agent tasks, rather than using the
    generic `AgentTeam.process(**kwargs)` method directly.

    Subclasses would typically encapsulate an `AgentTeam` instance and define
    methods that map domain-specific inputs to the underlying team's execution.
    """

    def __init__(self,
                 name: str,
                 wrapped_team_instance: Optional['AgentTeam'] = None):
        """
        Initializes the BaseAgentTeam.

        Args:
            name: A descriptive name for this specific team implementation.
            wrapped_team_instance: Optional. An instance of AgentTeam that this class
                                   will wrap and delegate to. If not provided, the subclass
                                   is responsible for initializing its own team instance.
        """
        self.name: str = name
        self._wrapped_team: Optional[Any] = wrapped_team_instance
        
        if self._wrapped_team:
            logger.info(f"BaseAgentTeam '{self.name}' initialized, wrapping an instance of "
                        f"'{self._wrapped_team.__class__.__name__}'.")
        else:
            logger.info(f"BaseAgentTeam '{self.name}' initialized without a pre-wrapped instance. "
                        "Subclass should handle team setup.")

    @property
    def wrapped_team(self) -> Optional[Any]:
        """Provides access to the wrapped AgentTeam instance."""
        return self._wrapped_team

    @abstractmethod
    async def start(self) -> None:
        """
        Starts the team. Subclasses should implement this to delegate
        to the start method of their wrapped AgentTeam.
        """
        pass

    @abstractmethod
    async def stop(self, timeout: float = 10.0) -> None:
        """
        Stops the team. Subclasses should implement this to delegate
        to the stop method of their wrapped AgentTeam.
        """
        pass

    @property
    @abstractmethod
    def is_running(self) -> bool:
        """
        Checks if the team is currently running. Subclasses should implement
        this to delegate to the is_running property of their wrapped instance.
        """
        pass
    
    def __repr__(self) -> str:
        running_status = "N/A (not implemented by subclass)"
        try:
            running_status = str(self.is_running)
        except NotImplementedError:
            pass
            
        return (f"<{self.__class__.__name__} name='{self.name}', "
                f"wraps='{self._wrapped_team.__class__.__name__ if self._wrapped_team else 'NoneInternal'}', "
                f"is_running={running_status}>")
