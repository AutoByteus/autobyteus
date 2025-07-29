# file: autobyteus/autobyteus/workflow/handlers/workflow_event_handler_registry.py
import logging
from typing import Dict, Type, Optional

from autobyteus.workflow.handlers.base_workflow_event_handler import BaseWorkflowEventHandler
from autobyteus.workflow.events.workflow_events import BaseWorkflowEvent

logger = logging.getLogger(__name__)

class WorkflowEventHandlerRegistry:
    """Manages registration and retrieval of workflow event handlers."""
    def __init__(self):
        self._handlers: Dict[Type[BaseWorkflowEvent], BaseWorkflowEventHandler] = {}
        logger.info("WorkflowEventHandlerRegistry initialized.")

    def register(self, event_class: Type[BaseWorkflowEvent], handler_instance: BaseWorkflowEventHandler):
        if not issubclass(event_class, BaseWorkflowEvent):
            raise TypeError("Can only register handlers for BaseWorkflowEvent subclasses.")
        self._handlers[event_class] = handler_instance
        logger.info(f"Handler '{type(handler_instance).__name__}' registered for event '{event_class.__name__}'.")

    def get_handler(self, event_class: Type[BaseWorkflowEvent]) -> Optional[BaseWorkflowEventHandler]:
        return self._handlers.get(event_class)
