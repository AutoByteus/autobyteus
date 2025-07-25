# file: autobyteus/autobyteus/agent/tool_execution_result_processor/processor_definition.py
import logging
from typing import Type, TYPE_CHECKING

if TYPE_CHECKING:
    from .base_processor import BaseToolExecutionResultProcessor

logger = logging.getLogger(__name__)

class ToolExecutionResultProcessorDefinition:
    """
    Represents the definition of a tool execution result processor.
    Contains its registered name and the class itself.
    """
    def __init__(self, name: str, processor_class: Type['BaseToolExecutionResultProcessor']):
        """
        Initializes the ToolExecutionResultProcessorDefinition.

        Args:
            name: The unique registered name of the processor.
            processor_class: The class of the tool execution result processor.

        Raises:
            ValueError: If name is empty or processor_class is not a type.
        """
        if not name or not isinstance(name, str):
            raise ValueError("Tool Execution Result Processor name must be a non-empty string.")
        if not isinstance(processor_class, type):
            raise ValueError("processor_class must be a class type.")
        
        self.name: str = name
        self.processor_class: Type['BaseToolExecutionResultProcessor'] = processor_class
        logger.debug(f"ToolExecutionResultProcessorDefinition created: name='{name}', class='{processor_class.__name__}'.")

    def __repr__(self) -> str:
        return f"<ToolExecutionResultProcessorDefinition name='{self.name}', class='{self.processor_class.__name__}'>"
