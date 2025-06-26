# file: autobyteus/autobyteus/agent/hooks/base_phase_hook.py
import logging
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from autobyteus.agent.phases import AgentOperationalPhase
from .hook_meta import PhaseHookMeta

if TYPE_CHECKING:
    from autobyteus.agent.context import AgentContext

logger = logging.getLogger(__name__)

class BasePhaseHook(ABC, metaclass=PhaseHookMeta):
    """
    Abstract base class for creating hooks that execute on specific agent
    phase transitions.

    Subclasses must define the `source_phase` and `target_phase` to specify
    the exact transition they are interested in, and implement the `execute`
    method for their custom logic.
    """

    @classmethod
    def get_name(cls) -> str:
        """
        Returns the unique registration name for this hook.
        Defaults to the class name. Can be overridden by subclasses.
        """
        return cls.__name__

    @property
    @abstractmethod
    def source_phase(self) -> AgentOperationalPhase:
        """The source phase for the transition this hook targets."""
        raise NotImplementedError

    @property
    @abstractmethod
    def target_phase(self) -> AgentOperationalPhase:
        """The target phase for the transition this hook targets."""
        raise NotImplementedError

    @abstractmethod
    async def execute(self, context: 'AgentContext') -> None:
        """
        The method executed when the specified phase transition occurs.

        Args:
            context: The agent's context at the time of the transition.
        """
        raise NotImplementedError

    def __repr__(self) -> str:
        # Use try-except in case properties are not yet implemented during introspection
        try:
            return (f"<{self.__class__.__name__} "
                    f"source='{self.source_phase.value}' "
                    f"target='{self.target_phase.value}'>")
        except (NotImplementedError, AttributeError):
            return f"<{self.__class__.__name__} (unconfigured)>"
