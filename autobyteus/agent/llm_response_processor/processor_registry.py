# file: autobyteus/autobyteus/agent/llm_response_processor/processor_registry.py
import logging
from typing import TYPE_CHECKING, Dict, List, Optional, Type

from autobyteus.utils.singleton import SingletonMeta
from .processor_definition import LLMResponseProcessorDefinition
if TYPE_CHECKING:
    from .base_processor import BaseLLMResponseProcessor

logger = logging.getLogger(__name__)

class LLMResponseProcessorRegistry(metaclass=SingletonMeta):
    """
    A singleton registry for LLMResponseProcessorDefinition objects.
    Processors are typically auto-registered via LLMResponseProcessorMeta.
    """

    def __init__(self):
        """Initializes the LLMResponseProcessorRegistry with an empty store."""
        self._definitions: Dict[str, LLMResponseProcessorDefinition] = {}
        logger.info("LLMResponseProcessorRegistry initialized.")

    def register_processor(self, definition: LLMResponseProcessorDefinition) -> None:
        """
        Registers an LLM response processor definition.
        If a definition with the same name already exists, it will be overwritten,
        and a warning will be logged.

        Args:
            definition: The LLMResponseProcessorDefinition object to register.

        Raises:
            TypeError: If the definition is not an instance of LLMResponseProcessorDefinition.
        """
        if not isinstance(definition, LLMResponseProcessorDefinition):
            raise TypeError(f"Expected LLMResponseProcessorDefinition instance, got {type(definition).__name__}.")

        processor_name = definition.name
        if processor_name in self._definitions:
            logger.warning(f"Overwriting existing LLM response processor definition for name: '{processor_name}'.")
        
        self._definitions[processor_name] = definition
        logger.info(f"LLM response processor definition '{processor_name}' (class: '{definition.processor_class.__name__}') registered successfully.")

    def get_processor_definition(self, name: str) -> Optional[LLMResponseProcessorDefinition]:
        """
        Retrieves an LLM response processor definition by its name.

        Args:
            name: The name of the LLM response processor definition to retrieve.

        Returns:
            The LLMResponseProcessorDefinition object if found, otherwise None.
        """
        if not isinstance(name, str):
            logger.warning(f"Attempted to retrieve LLM response processor definition with non-string name: {type(name).__name__}.")
            return None
        definition = self._definitions.get(name)
        if not definition:
            logger.debug(f"LLM response processor definition with name '{name}' not found in registry.")
        return definition

    def get_processor(self, name: str) -> Optional['BaseLLMResponseProcessor']:
        """
        Retrieves an instance of an LLM response processor by its name.

        Args:
            name: The name of the LLM response processor to retrieve.

        Returns:
            An instance of the BaseLLMResponseProcessor if found and instantiable, otherwise None.
        """
        definition = self.get_processor_definition(name)
        if definition:
            try:
                return definition.processor_class()
            except Exception as e:
                logger.error(f"Failed to instantiate LLM response processor '{name}' from class '{definition.processor_class.__name__}': {e}", exc_info=True)
                return None
        return None

    def list_processor_names(self) -> List[str]:
        """
        Returns a list of names of all registered LLM response processor definitions.

        Returns:
            A list of strings, where each string is a registered processor name.
        """
        return list(self._definitions.keys())

    def get_all_definitions(self) -> Dict[str, LLMResponseProcessorDefinition]:
        """
        Returns a shallow copy of the dictionary containing all registered LLM response processor definitions.
        """
        return dict(self._definitions)

    def clear(self) -> None:
        """Removes all definitions from the registry."""
        count = len(self._definitions)
        self._definitions.clear()
        logger.info(f"Cleared {count} definitions from the LLMResponseProcessorRegistry.")

    def __len__(self) -> int:
        """Returns the number of registered LLM response processor definitions."""
        return len(self._definitions)

    def __contains__(self, name: str) -> bool:
        """Checks if a processor definition is in the registry by name."""
        if isinstance(name, str):
            return name in self._definitions
        return False

default_llm_response_processor_registry = LLMResponseProcessorRegistry()
