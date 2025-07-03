# file: autobyteus/autobyteus/agent/hooks/hook_meta.py
import logging
from abc import ABCMeta

from .hook_registry import default_phase_hook_registry
from .hook_definition import PhaseHookDefinition

logger = logging.getLogger(__name__)

class PhaseHookMeta(ABCMeta):
    """
    Metaclass for BasePhaseHook that automatically registers concrete
    hook subclasses with the default_phase_hook_registry.
    Registration uses the name obtained from the class method `get_name()`.
    """
    def __init__(cls, name, bases, dct):
        super().__init__(name, bases, dct)

        if name == 'BasePhaseHook' or getattr(cls, "__abstractmethods__", None):
            logger.debug(f"Skipping registration for abstract phase hook class: {name}")
            return

        try:
            hook_name = cls.get_name()

            if not hook_name or not isinstance(hook_name, str):
                logger.error(f"Phase hook class {name} must return a valid string from static get_name(). Skipping registration.")
                return
            
            definition = PhaseHookDefinition(name=hook_name, hook_class=cls)
            default_phase_hook_registry.register_hook(definition)
            logger.info(f"Auto-registered phase hook: '{hook_name}' from class {name} (no schema).")

        except AttributeError as e:
            logger.error(f"Phase hook class {name} is missing required static/class method 'get_name' ({e}). Skipping registration.")
        except Exception as e:
            logger.error(f"Failed to auto-register phase hook class {name}: {e}", exc_info=True)
