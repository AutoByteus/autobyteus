# file: autobyteus/autobyteus/agent/llm_response_processor/processor_definition.py
import logging
from typing import Type, TYPE_CHECKING

if TYPE_CHECKING:
    from .base_processor import BaseLLMResponseProcessor

logger = logging.getLogger(__name__)

class LLMResponseProcessorDefinition:
    """
    Represents the definition of an LLM response processor.
    Contains its registered name and the class itself.
    """
    def __init__(self, name: str, processor_class: Type['BaseLLMResponseProcessor']):
        """
        Initializes the LLMResponseProcessorDefinition.

        Args:
            name: The unique registered name of the processor.
            processor_class: The class of the LLM response processor.

        Raises:
            ValueError: If name is empty or processor_class is not a type.
        """
        if not name or not isinstance(name, str):
            raise ValueError("LLM Response Processor name must be a non-empty string.")
        if not isinstance(processor_class, type):
            raise ValueError("processor_class must be a class type.")
        
        self.name: str = name
        self.processor_class: Type['BaseLLMResponseProcessor'] = processor_class
        logger.debug(f"LLMResponseProcessorDefinition created: name='{name}', class='{processor_class.__name__}'.")

    def __repr__(self) -> str:
        return f"<LLMResponseProcessorDefinition name='{self.name}', class='{self.processor_class.__name__}'>"
