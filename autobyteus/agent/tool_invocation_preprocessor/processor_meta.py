import logging
from abc import ABCMeta

from .processor_registry import default_tool_invocation_preprocessor_registry
from .processor_definition import ToolInvocationPreprocessorDefinition

logger = logging.getLogger(__name__)


class ToolInvocationPreprocessorMeta(ABCMeta):
    """
    Metaclass to auto-register concrete preprocessors.
    """
    def __init__(cls, name, bases, dct):
        super().__init__(name, bases, dct)

        if name == "BaseToolInvocationPreprocessor" or getattr(cls, "__abstractmethods__", None):
            logger.debug(f"Skipping registration for abstract tool invocation preprocessor class: {name}")
            return

        try:
            processor_name = cls.get_name()
            if not processor_name or not isinstance(processor_name, str):
                logger.error(f"Tool invocation preprocessor class {name} must return valid string from get_name(); skipping.")
                return
            definition = ToolInvocationPreprocessorDefinition(name=processor_name, processor_class=cls)
            default_tool_invocation_preprocessor_registry.register_preprocessor(definition)
            logger.info(f"Auto-registered tool invocation preprocessor '{processor_name}' from class {name}.")
        except AttributeError as e:
            logger.error(f"Tool invocation preprocessor class {name} missing required methods ({e}); skipping registration.")
        except Exception as e:
            logger.error(f"Failed to auto-register tool invocation preprocessor class {name}: {e}", exc_info=True)

