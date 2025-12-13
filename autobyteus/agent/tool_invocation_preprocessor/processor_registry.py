import logging
from typing import TYPE_CHECKING, Dict, List, Optional

from autobyteus.utils.singleton import SingletonMeta
from autobyteus.agent.processor_option import ProcessorOption
from .processor_definition import ToolInvocationPreprocessorDefinition

if TYPE_CHECKING:
    from .base_preprocessor import BaseToolInvocationPreprocessor

logger = logging.getLogger(__name__)


class ToolInvocationPreprocessorRegistry(metaclass=SingletonMeta):
    """
    Registry for ToolInvocationPreprocessor definitions.
    """
    def __init__(self):
        self._definitions: Dict[str, ToolInvocationPreprocessorDefinition] = {}
        logger.info("ToolInvocationPreprocessorRegistry initialized.")

    def register_preprocessor(self, definition: ToolInvocationPreprocessorDefinition) -> None:
        if not isinstance(definition, ToolInvocationPreprocessorDefinition):
            raise TypeError(f"Expected ToolInvocationPreprocessorDefinition, got {type(definition).__name__}")
        name = definition.name
        if name in self._definitions:
            logger.warning(f"Overwriting existing tool invocation preprocessor definition '{name}'.")
        self._definitions[name] = definition
        logger.info(f"Tool invocation preprocessor definition '{name}' registered.")

    def get_preprocessor_definition(self, name: str) -> Optional[ToolInvocationPreprocessorDefinition]:
        return self._definitions.get(name)

    def get_preprocessor(self, name: str) -> Optional['BaseToolInvocationPreprocessor']:
        definition = self.get_preprocessor_definition(name)
        if definition:
            try:
                return definition.processor_class()
            except Exception as e:
                logger.error(f"Failed to instantiate tool invocation preprocessor '{name}': {e}", exc_info=True)
                return None
        return None

    def list_preprocessor_names(self) -> List[str]:
        return list(self._definitions.keys())

    # Backwards-compatible alias used by some services
    def get_processor(self, name: str) -> Optional['BaseToolInvocationPreprocessor']:
        return self.get_preprocessor(name)

    def get_ordered_processor_options(self) -> List[ProcessorOption]:
        definitions = list(self._definitions.values())
        sorted_defs = sorted(definitions, key=lambda d: d.processor_class.get_order())
        return [ProcessorOption(name=d.name, is_mandatory=d.processor_class.is_mandatory()) for d in sorted_defs]

    def get_all_definitions(self) -> Dict[str, ToolInvocationPreprocessorDefinition]:
        return dict(self._definitions)


default_tool_invocation_preprocessor_registry = ToolInvocationPreprocessorRegistry()
