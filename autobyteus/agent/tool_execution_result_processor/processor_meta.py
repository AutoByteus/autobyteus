# file: autobyteus/autobyteus/agent/tool_execution_result_processor/processor_meta.py
import logging
from abc import ABCMeta

from .processor_registry import default_tool_execution_result_processor_registry
from .processor_definition import ToolExecutionResultProcessorDefinition

logger = logging.getLogger(__name__)

class ToolExecutionResultProcessorMeta(ABCMeta):
    """
    Metaclass for BaseToolExecutionResultProcessor that automatically registers
    concrete processor subclasses with the default registry.
    """
    def __init__(cls, name, bases, dct):
        super().__init__(name, bases, dct)

        if name == 'BaseToolExecutionResultProcessor' or getattr(cls, "__abstractmethods__", None):
            logger.debug(f"Skipping registration for abstract tool execution result processor class: {name}")
            return

        try:
            processor_name = cls.get_name()

            if not processor_name or not isinstance(processor_name, str):
                logger.error(f"Tool execution result processor class {name} must return a valid string from get_name(). Skipping.")
                return
            
            definition = ToolExecutionResultProcessorDefinition(name=processor_name, processor_class=cls)
            default_tool_execution_result_processor_registry.register_processor(definition)
            logger.info(f"Auto-registered tool execution result processor: '{processor_name}' from class {name}.")

        except AttributeError as e:
            logger.error(f"Tool execution result processor class {name} is missing 'get_name' method ({e}). Skipping registration.")
        except Exception as e:
            logger.error(f"Failed to auto-register tool execution result processor class {name}: {e}", exc_info=True)
