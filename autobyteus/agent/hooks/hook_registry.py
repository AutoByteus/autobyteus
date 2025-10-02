# file: autobyteus/autobyteus/agent/hooks/hook_registry.py
import logging
from typing import TYPE_CHECKING, Dict, List, Optional

from autobyteus.utils.singleton import SingletonMeta
from autobyteus.agent.processor_option import HookOption
from .hook_definition import PhaseHookDefinition

if TYPE_CHECKING:
    from .base_phase_hook import BasePhaseHook

logger = logging.getLogger(__name__)

class PhaseHookRegistry(metaclass=SingletonMeta):
    """
    A singleton registry for PhaseHookDefinition objects.
    Hooks are typically auto-registered via PhaseHookMeta.
    """

    def __init__(self):
        """Initializes the PhaseHookRegistry with an empty store."""
        self._definitions: Dict[str, PhaseHookDefinition] = {}
        logger.info("PhaseHookRegistry initialized.")

    def register_hook(self, definition: PhaseHookDefinition) -> None:
        """
        Registers a phase hook definition.
        """
        if not isinstance(definition, PhaseHookDefinition):
            raise TypeError(f"Expected PhaseHookDefinition instance, got {type(definition).__name__}.")

        hook_name = definition.name
        if hook_name in self._definitions:
            logger.warning(f"Overwriting existing phase hook definition for name: '{hook_name}'.")
        
        self._definitions[hook_name] = definition
        logger.info(f"Phase hook definition '{hook_name}' (class: '{definition.hook_class.__name__}') registered successfully.")

    def get_hook_definition(self, name: str) -> Optional[PhaseHookDefinition]:
        """
        Retrieves a phase hook definition by its name.
        """
        if not isinstance(name, str):
            logger.warning(f"Attempted to retrieve hook definition with non-string name: {type(name).__name__}.")
            return None
        definition = self._definitions.get(name)
        if not definition:
            logger.debug(f"Phase hook definition with name '{name}' not found in registry.")
        return definition

    def get_hook(self, name: str) -> Optional['BasePhaseHook']:
        """
        Retrieves an instance of a phase hook by its name.
        """
        definition = self.get_hook_definition(name)
        if definition:
            try:
                return definition.hook_class()
            except Exception as e:
                logger.error(f"Failed to instantiate phase hook '{name}' from class '{definition.hook_class.__name__}': {e}", exc_info=True)
                return None
        return None

    def list_hook_names(self) -> List[str]:
        """
        Returns an unordered list of names of all registered phase hook definitions.
        """
        return list(self._definitions.keys())

    def get_ordered_hook_options(self) -> List[HookOption]:
        """
        Returns a list of HookOption objects, sorted by their execution order.
        """
        definitions = list(self._definitions.values())
        sorted_definitions = sorted(definitions, key=lambda d: d.hook_class.get_order())
        return [
            HookOption(
                name=d.name,
                is_mandatory=d.hook_class.is_mandatory()
            ) for d in sorted_definitions
        ]

    def get_all_definitions(self) -> Dict[str, PhaseHookDefinition]:
        """
        Returns a shallow copy of the dictionary containing all registered phase hook definitions.
        """
        return dict(self._definitions)

    def clear(self) -> None:
        """Removes all definitions from the registry."""
        count = len(self._definitions)
        self._definitions.clear()
        logger.info(f"Cleared {count} definitions from the PhaseHookRegistry.")
        
    def __len__(self) -> int:
        """Returns the number of registered hook definitions."""
        return len(self._definitions)

    def __contains__(self, name: str) -> bool:
        """Checks if a hook definition is in the registry by name."""
        if isinstance(name, str):
            return name in self._definitions
        return False

# Default instance of the registry
default_phase_hook_registry = PhaseHookRegistry()
