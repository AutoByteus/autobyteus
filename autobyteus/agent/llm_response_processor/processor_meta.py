# file: autobyteus/autobyteus/agent/llm_response_processor/processor_meta.py
import logging
from abc import ABCMeta

from .processor_registry import default_llm_response_processor_registry
from .processor_definition import LLMResponseProcessorDefinition

logger = logging.getLogger(__name__)

class LLMResponseProcessorMeta(ABCMeta):
    """
    Metaclass for BaseLLMResponseProcessor that automatically registers concrete
    processor subclasses with the default_llm_response_processor_registry.
    Registration uses the name obtained from the class method `get_name()`.
    """
    def __init__(cls, name, bases, dct):
        super().__init__(name, bases, dct)

        if name == 'BaseLLMResponseProcessor' or getattr(cls, "__abstractmethods__", None):
            logger.debug(f"Skipping registration for abstract LLM response processor class: {name}")
            return

        try:
            processor_name = cls.get_name()

            if not processor_name or not isinstance(processor_name, str):
                logger.error(f"LLM response processor class {name} must return a valid string from static get_name(). Skipping registration.")
                return
            
            definition = LLMResponseProcessorDefinition(name=processor_name, processor_class=cls)
            default_llm_response_processor_registry.register_processor(definition)
            logger.info(f"Auto-registered LLM response processor: '{processor_name}' from class {name} (no schema).")

        except AttributeError as e:
            logger.error(f"LLM response processor class {name} is missing required static/class method 'get_name' ({e}). Skipping registration.")
        except Exception as e:
            logger.error(f"Failed to auto-register LLM response processor class {name}: {e}", exc_info=True)
