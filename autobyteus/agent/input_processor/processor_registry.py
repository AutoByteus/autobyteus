# file: autobyteus/autobyteus/agent/input_processor/processor_registry.py
import logging
from typing import TYPE_CHECKING, Dict, List, Optional, Type

from autobyteus.utils.singleton import SingletonMeta
from autobyteus.agent.processor_option import ProcessorOption
from .processor_definition import AgentUserInputMessageProcessorDefinition
if TYPE_CHECKING:
    from .base_user_input_processor import BaseAgentUserInputMessageProcessor

logger = logging.getLogger(__name__)

class AgentUserInputMessageProcessorRegistry(metaclass=SingletonMeta):
    """
    A singleton registry for AgentUserInputMessageProcessorDefinition objects.
    Processors are typically auto-registered via AgentUserInputMessageProcessorMeta.
    """

    def __init__(self):
        """Initializes the AgentUserInputMessageProcessorRegistry with an empty store."""
        self._definitions: Dict[str, AgentUserInputMessageProcessorDefinition] = {}
        logger.info("AgentUserInputMessageProcessorRegistry initialized.")

    def register_processor(self, definition: AgentUserInputMessageProcessorDefinition) -> None:
        """
        Registers an input processor definition.
        """
        if not isinstance(definition, AgentUserInputMessageProcessorDefinition):
            raise TypeError(f"Expected AgentUserInputMessageProcessorDefinition instance, got {type(definition).__name__}.")

        processor_name = definition.name
        if processor_name in self._definitions:
            logger.warning(f"Overwriting existing input processor definition for name: '{processor_name}'.")
        
        self._definitions[processor_name] = definition
        logger.info(f"Input processor definition '{processor_name}' (class: '{definition.processor_class.__name__}') registered successfully.")

    def get_processor_definition(self, name: str) -> Optional[AgentUserInputMessageProcessorDefinition]:
        """
        Retrieves an input processor definition by its name.
        """
        if not isinstance(name, str):
            logger.warning(f"Attempted to retrieve input processor definition with non-string name: {type(name).__name__}.")
            return None
        definition = self._definitions.get(name)
        if not definition:
            logger.debug(f"Input processor definition with name '{name}' not found in registry.")
        return definition

    def get_processor(self, name: str) -> Optional['BaseAgentUserInputMessageProcessor']:
        """
        Retrieves an instance of an input processor by its name.
        """
        definition = self.get_processor_definition(name)
        if definition:
            try:
                return definition.processor_class()
            except Exception as e:
                logger.error(f"Failed to instantiate input processor '{name}' from class '{definition.processor_class.__name__}': {e}", exc_info=True)
                return None
        return None

    def list_processor_names(self) -> List[str]:
        """
        Returns an unordered list of names of all registered input processor definitions.
        """
        return list(self._definitions.keys())

    def get_ordered_processor_options(self) -> List[ProcessorOption]:
        """
        Returns a list of ProcessorOption objects, sorted by their execution order.
        """
        definitions = list(self._definitions.values())
        sorted_definitions = sorted(definitions, key=lambda d: d.processor_class.get_order())
        return [
            ProcessorOption(
                name=d.name,
                is_mandatory=d.processor_class.is_mandatory()
            ) for d in sorted_definitions
        ]

    def get_all_definitions(self) -> Dict[str, AgentUserInputMessageProcessorDefinition]:
        """
        Returns a shallow copy of the dictionary containing all registered input processor definitions.
        """
        return dict(self._definitions)

    def clear(self) -> None:
        """Removes all definitions from the registry."""
        count = len(self._definitions)
        self._definitions.clear()
        logger.info(f"Cleared {count} definitions from the AgentUserInputMessageProcessorRegistry.")

    def __len__(self) -> int:
        """Returns the number of registered input processor definitions."""
        return len(self._definitions)

    def __contains__(self, name: str) -> bool:
        """Checks if a processor definition is in the registry by name."""
        if isinstance(name, str):
            return name in self._definitions
        return False

# Default instance of the registry
default_input_processor_registry = AgentUserInputMessageProcessorRegistry()
