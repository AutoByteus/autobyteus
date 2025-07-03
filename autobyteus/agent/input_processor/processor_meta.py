# file: autobyteus/autobyteus/agent/input_processor/processor_meta.py
import logging
from abc import ABCMeta

# Import the global registry and definition class
from .processor_registry import default_input_processor_registry
from .processor_definition import AgentUserInputMessageProcessorDefinition

logger = logging.getLogger(__name__)

class AgentUserInputMessageProcessorMeta(ABCMeta):
    """
    Metaclass for BaseAgentUserInputMessageProcessor that automatically registers concrete
    processor subclasses with the default_input_processor_registry.
    Registration uses the name obtained from the class method `get_name()`.
    """
    def __init__(cls, name, bases, dct):
        """
        Called when a class using this metaclass is defined.
        """
        super().__init__(name, bases, dct)

        # Prevent registration of the BaseAgentUserInputMessageProcessor class itself
        # or other explicitly abstract classes.
        if name == 'BaseAgentUserInputMessageProcessor' or getattr(cls, "__abstractmethods__", None):
            logger.debug(f"Skipping registration for abstract input processor class: {name}")
            return

        try:
            # Get static/class info from the class being defined
            processor_name = cls.get_name()

            if not processor_name or not isinstance(processor_name, str):
                logger.error(f"Input processor class {name} must return a valid string from static get_name(). Skipping registration.")
                return
            
            # Create definition using name and the class itself
            definition = AgentUserInputMessageProcessorDefinition(name=processor_name, processor_class=cls)
            default_input_processor_registry.register_processor(definition)
            logger.info(f"Auto-registered input processor: '{processor_name}' from class {name} (no schema).")

        except AttributeError as e:
            # Catch if get_name is missing
            logger.error(f"Input processor class {name} is missing required static/class method 'get_name' ({e}). Skipping registration.")
        except Exception as e:
            logger.error(f"Failed to auto-register input processor class {name}: {e}", exc_info=True)
