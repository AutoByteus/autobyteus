# file: autobyteus/autobyteus/agent/tool_execution_result_processor/processor_registry.py
import logging
from typing import TYPE_CHECKING, Dict, List, Optional

from autobyteus.utils.singleton import SingletonMeta
from autobyteus.agent.processor_option import ProcessorOption
from .processor_definition import ToolExecutionResultProcessorDefinition

if TYPE_CHECKING:
    from .base_processor import BaseToolExecutionResultProcessor

logger = logging.getLogger(__name__)

class ToolExecutionResultProcessorRegistry(metaclass=SingletonMeta):
    """
    A singleton registry for ToolExecutionResultProcessorDefinition objects.
    Processors are typically auto-registered via ToolExecutionResultProcessorMeta.
    """

    def __init__(self):
        """Initializes the registry with an empty store."""
        self._definitions: Dict[str, ToolExecutionResultProcessorDefinition] = {}
        logger.info("ToolExecutionResultProcessorRegistry initialized.")

    def register_processor(self, definition: ToolExecutionResultProcessorDefinition) -> None:
        """
        Registers a tool execution result processor definition.
        """
        if not isinstance(definition, ToolExecutionResultProcessorDefinition):
            raise TypeError(f"Expected ToolExecutionResultProcessorDefinition instance, got {type(definition).__name__}.")

        processor_name = definition.name
        if processor_name in self._definitions:
            logger.warning(f"Overwriting existing tool execution result processor definition for name: '{processor_name}'.")
        
        self._definitions[processor_name] = definition
        logger.info(f"Tool execution result processor definition '{processor_name}' registered successfully.")

    def get_processor_definition(self, name: str) -> Optional[ToolExecutionResultProcessorDefinition]:
        """
        Retrieves a processor definition by its name.
        """
        return self._definitions.get(name)

    def get_processor(self, name: str) -> Optional['BaseToolExecutionResultProcessor']:
        """
        Retrieves an instance of a processor by its name.
        """
        definition = self.get_processor_definition(name)
        if definition:
            try:
                return definition.processor_class()
            except Exception as e:
                logger.error(f"Failed to instantiate tool execution result processor '{name}': {e}", exc_info=True)
                return None
        return None

    def list_processor_names(self) -> List[str]:
        """
        Returns an unordered list of names of all registered processor definitions.
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

    def get_all_definitions(self) -> Dict[str, ToolExecutionResultProcessorDefinition]:
        """
        Returns a dictionary of all registered processor definitions.
        """
        return dict(self._definitions)

# Default instance of the registry
default_tool_execution_result_processor_registry = ToolExecutionResultProcessorRegistry()
