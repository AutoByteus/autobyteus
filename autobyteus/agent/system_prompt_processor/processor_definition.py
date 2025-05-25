# file: autobyteus/autobyteus/agent/system_prompt_processor/processor_definition.py
import logging
from typing import Type, TYPE_CHECKING

if TYPE_CHECKING:
    from .base_processor import BaseSystemPromptProcessor

logger = logging.getLogger(__name__)

class SystemPromptProcessorDefinition:
    """
    Represents the definition of a system prompt processor.
    Contains its registered name and the class itself.
    """
    def __init__(self, name: str, processor_class: Type['BaseSystemPromptProcessor']):
        """
        Initializes the SystemPromptProcessorDefinition.

        Args:
            name: The unique registered name of the processor.
            processor_class: The class of the system prompt processor.

        Raises:
            ValueError: If name is empty or processor_class is not a type.
        """
        if not name or not isinstance(name, str):
            raise ValueError("System Prompt Processor name must be a non-empty string.")
        if not isinstance(processor_class, type):
            raise ValueError("processor_class must be a class type.")
        
        # from .base_processor import BaseSystemPromptProcessor # Delayed import for check
        # if not issubclass(processor_class, BaseSystemPromptProcessor):
        #    raise ValueError(f"processor_class '{processor_class.__name__}' must be a subclass of BaseSystemPromptProcessor.")

        self.name: str = name
        self.processor_class: Type['BaseSystemPromptProcessor'] = processor_class
        logger.debug(f"SystemPromptProcessorDefinition created: name='{name}', class='{processor_class.__name__}'.")

    def __repr__(self) -> str:
        return f"<SystemPromptProcessorDefinition name='{self.name}', class='{self.processor_class.__name__}'>"
