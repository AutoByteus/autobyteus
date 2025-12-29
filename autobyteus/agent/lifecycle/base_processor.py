# file: autobyteus/agent/lifecycle/base_processor.py
"""
Base class for lifecycle processors.
Follows the same pattern as other processors (InputProcessor, LLMResponseProcessor, etc.)
"""
import logging
from abc import ABC, abstractmethod, ABCMeta
from typing import TYPE_CHECKING, Any, Dict

from autobyteus.agent.lifecycle.events import LifecycleEvent

if TYPE_CHECKING:
    from autobyteus.agent.context import AgentContext

logger = logging.getLogger(__name__)

class LifecycleEventProcessorMeta(ABCMeta):
    """
    Metaclass that automatically registers subclasses of BaseLifecycleEventProcessor.
    """
    def __new__(mcs, name, bases, namespace):
        cls = super().__new__(mcs, name, bases, namespace)
        
        # Avoid registering the base abstract class itself
        if name != "BaseLifecycleEventProcessor":
             # Avoid circular imports by importing inside the method
            from autobyteus.agent.lifecycle.processor_definition import LifecycleEventProcessorDefinition
            from autobyteus.agent.lifecycle.processor_registry import default_lifecycle_event_processor_registry
            
            # Use get_name() if available, otherwise class name. 
            # Note: get_name is a classmethod on BaseLifecycleEventProcessor, but cls is not fully formed?
            # Actually, standard pattern calls cls.get_name() if defined.
            try:
                # We can instantiate a definition using the class
                reg_name = cls.get_name()
                definition = LifecycleEventProcessorDefinition(name=reg_name, processor_class=cls)
                default_lifecycle_event_processor_registry.register_processor(definition)
            except Exception as e:
                # This might happen if get_name fails or other issues during definition creation
                # Logging as warning because intermediate abstract classes might fail
                logger.debug(f"Skipping auto-registration for {name}: {e}")

        return cls


class BaseLifecycleEventProcessor(ABC, metaclass=LifecycleEventProcessorMeta):
    """
    Abstract base class for lifecycle event processors.
    
    Users extend this class to add custom logic at specific lifecycle events.
    Only requires specifying a single event (unlike Phase Hooks which required
    source + target phase).
    
    Example:
        class MySetupProcessor(BaseLifecycleEventProcessor):
            @property
            def event(self) -> LifecycleEvent:
                return LifecycleEvent.AGENT_READY
            
            async def process(self, context, event_data):
                print("Agent is ready!")
    """

    @classmethod
    def get_name(cls) -> str:
        """
        Returns the unique name for this processor.
        Defaults to the class name.
        """
        return cls.__name__

    @classmethod
    def get_order(cls) -> int:
        """
        Returns the execution order. Lower numbers execute earlier.
        Defaults to 500 (normal priority).
        """
        return 500

    @classmethod
    def is_mandatory(cls) -> bool:
        """
        Returns True if this processor logic is mandatory and cannot be skipped by user config.
        Defaults to False.
        """
        return False

    @property
    @abstractmethod
    def event(self) -> LifecycleEvent:
        """The lifecycle event this processor handles."""
        raise NotImplementedError

    @abstractmethod
    async def process(self, context: 'AgentContext', event_data: Dict[str, Any]) -> None:
        """
        Execute processor logic.
        
        Args:
            context: The agent's context with full state access.
            event_data: Event-specific data (e.g., tool_name for tool events).
        """
        raise NotImplementedError

    def __repr__(self) -> str:
        try:
            return f"<{self.__class__.__name__} event='{self.event.value}'>"
        except (NotImplementedError, AttributeError):
            return f"<{self.__class__.__name__} (unconfigured)>"
