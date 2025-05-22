# file: autobyteus/autobyteus/agent/input_processor/processor_definition.py
import logging
from typing import Type, TYPE_CHECKING

if TYPE_CHECKING:
    from .base_user_input_processor import BaseAgentUserInputMessageProcessor

logger = logging.getLogger(__name__)

class AgentUserInputMessageProcessorDefinition:
    """
    Represents the definition of an agent user input message processor.
    Contains its registered name and the class itself.
    """
    def __init__(self, name: str, processor_class: Type['BaseAgentUserInputMessageProcessor']):
        """
        Initializes the AgentUserInputMessageProcessorDefinition.

        Args:
            name: The unique registered name of the processor.
            processor_class: The class of the input processor.

        Raises:
            ValueError: If name is empty or processor_class is not a type.
        """
        if not name or not isinstance(name, str):
            raise ValueError("Processor name must be a non-empty string.")
        if not isinstance(processor_class, type): # Check if it's actually a class
            raise ValueError("processor_class must be a class type.")
        
        # Further check if it's a subclass of BaseAgentUserInputMessageProcessor might be too restrictive
        # here if base class is not yet defined due to import cycles, metaclass handles this better.
        # from .base_user_input_processor import BaseAgentUserInputMessageProcessor # Delayed import for check
        # if not issubclass(processor_class, BaseAgentUserInputMessageProcessor):
        #    raise ValueError(f"processor_class '{processor_class.__name__}' must be a subclass of BaseAgentUserInputMessageProcessor.")

        self.name: str = name
        self.processor_class: Type['BaseAgentUserInputMessageProcessor'] = processor_class
        logger.debug(f"AgentUserInputMessageProcessorDefinition created: name='{name}', class='{processor_class.__name__}'.")

    def __repr__(self) -> str:
        return f"<AgentUserInputMessageProcessorDefinition name='{self.name}', class='{self.processor_class.__name__}'>"
