# file: autobyteus/autobyteus/agent/system_prompt_processor/processor_registry.py
import logging
from typing import TYPE_CHECKING, Dict, List, Optional, Type

from autobyteus.utils.singleton import SingletonMeta
from .processor_definition import SystemPromptProcessorDefinition # Relative import

if TYPE_CHECKING:
    from .base_processor import BaseSystemPromptProcessor # Relative import

logger = logging.getLogger(__name__)

class SystemPromptProcessorRegistry(metaclass=SingletonMeta):
    """
    A singleton registry for SystemPromptProcessorDefinition objects.
    Processors are typically auto-registered via SystemPromptProcessorMeta.
    """

    def __init__(self):
        """Initializes the SystemPromptProcessorRegistry with an empty store."""
        self._definitions: Dict[str, SystemPromptProcessorDefinition] = {}
        logger.info("SystemPromptProcessorRegistry initialized.")

    def register_processor(self, definition: SystemPromptProcessorDefinition) -> None:
        """
        Registers a system prompt processor definition.
        If a definition with the same name already exists, it will be overwritten,
        and a warning will be logged.

        Args:
            definition: The SystemPromptProcessorDefinition object to register.

        Raises:
            TypeError: If the definition is not an instance of SystemPromptProcessorDefinition.
        """
        if not isinstance(definition, SystemPromptProcessorDefinition):
            raise TypeError(f"Expected SystemPromptProcessorDefinition instance, got {type(definition).__name__}.")

        processor_name = definition.name
        if processor_name in self._definitions:
            logger.warning(f"Overwriting existing system prompt processor definition for name: '{processor_name}'.")
        
        self._definitions[processor_name] = definition
        logger.info(f"System prompt processor definition '{processor_name}' (class: '{definition.processor_class.__name__}') registered successfully.")

    def get_processor_definition(self, name: str) -> Optional[SystemPromptProcessorDefinition]:
        """
        Retrieves a system prompt processor definition by its name.

        Args:
            name: The name of the system prompt processor definition to retrieve.

        Returns:
            The SystemPromptProcessorDefinition object if found, otherwise None.
        """
        if not isinstance(name, str):
            logger.warning(f"Attempted to retrieve system prompt processor definition with non-string name: {type(name).__name__}.")
            return None
        definition = self._definitions.get(name)
        if not definition:
            logger.debug(f"System prompt processor definition with name '{name}' not found in registry.")
        return definition
    
    def get_processor(self, name: str) -> Optional['BaseSystemPromptProcessor']:
        """
        Retrieves an instance of a system prompt processor by its name.

        Args:
            name: The name of the system prompt processor to retrieve.

        Returns:
            An instance of the BaseSystemPromptProcessor if found and instantiable, otherwise None.
        """
        definition = self.get_processor_definition(name)
        if definition:
            try:
                return definition.processor_class()
            except Exception as e:
                logger.error(f"Failed to instantiate system prompt processor '{name}' from class '{definition.processor_class.__name__}': {e}", exc_info=True)
                return None
        return None


    def list_processor_names(self) -> List[str]:
        """
        Returns a list of names of all registered system prompt processor definitions.

        Returns:
            A list of strings, where each string is a registered processor name.
        """
        return list(self._definitions.keys())

    def get_all_definitions(self) -> Dict[str, SystemPromptProcessorDefinition]:
        """
        Returns a shallow copy of the dictionary containing all registered system prompt processor definitions.

        Returns:
            A dictionary where keys are processor names and values are SystemPromptProcessorDefinition objects.
        """
        return dict(self._definitions)

    def clear(self) -> None:
        """Removes all definitions from the registry."""
        count = len(self._definitions)
        self._definitions.clear()
        logger.info(f"Cleared {count} definitions from the SystemPromptProcessorRegistry.")

    def __len__(self) -> int:
        """Returns the number of registered system prompt processor definitions."""
        return len(self._definitions)

    def __contains__(self, name: str) -> bool:
        """Checks if a processor definition is in the registry by name."""
        if isinstance(name, str):
            return name in self._definitions
        return False

# Default instance of the registry
default_system_prompt_processor_registry = SystemPromptProcessorRegistry()
