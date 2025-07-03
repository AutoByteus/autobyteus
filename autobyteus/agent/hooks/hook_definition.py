# file: autobyteus/autobyteus/agent/hooks/hook_definition.py
import logging
from typing import Type, TYPE_CHECKING

if TYPE_CHECKING:
    from .base_phase_hook import BasePhaseHook

logger = logging.getLogger(__name__)

class PhaseHookDefinition:
    """
    Represents the definition of a phase hook.
    Contains its registered name and the class itself.
    """
    def __init__(self, name: str, hook_class: Type['BasePhaseHook']):
        """
        Initializes the PhaseHookDefinition.

        Args:
            name: The unique registered name of the hook.
            hook_class: The class of the phase hook.

        Raises:
            ValueError: If name is empty or hook_class is not a type.
        """
        if not name or not isinstance(name, str):
            raise ValueError("Hook name must be a non-empty string.")
        if not isinstance(hook_class, type):
            raise ValueError("hook_class must be a class type.")
        
        self.name: str = name
        self.hook_class: Type['BasePhaseHook'] = hook_class
        logger.debug(f"PhaseHookDefinition created: name='{name}', class='{hook_class.__name__}'.")

    def __repr__(self) -> str:
        return f"<PhaseHookDefinition name='{self.name}', class='{self.hook_class.__name__}'>"
