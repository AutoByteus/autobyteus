# file: autobyteus/autobyteus/workflow/events/workflow_event_dispatcher.py
import logging
import traceback
from typing import TYPE_CHECKING

from autobyteus.workflow.events.workflow_events import BaseWorkflowEvent, WorkflowReadyEvent, ProcessUserMessageEvent

if TYPE_CHECKING:
    from autobyteus.workflow.context.workflow_context import WorkflowContext
    from autobyteus.workflow.handlers.workflow_event_handler_registry import WorkflowEventHandlerRegistry
    from autobyteus.workflow.phases.workflow_phase_manager import WorkflowPhaseManager

logger = logging.getLogger(__name__)

class WorkflowEventDispatcher:
    """Dispatches workflow events to their appropriate handlers."""

    def __init__(self,
                 event_handler_registry: 'WorkflowEventHandlerRegistry',
                 phase_manager: 'WorkflowPhaseManager'):
        self.registry = event_handler_registry
        self.phase_manager = phase_manager

    async def dispatch(self, event: BaseWorkflowEvent, context: 'WorkflowContext'):
        handler = self.registry.get_handler(type(event))
        workflow_id = context.workflow_id

        if not handler:
            logger.warning(f"Workflow '{workflow_id}': No handler for event '{type(event).__name__}'.")
            return

        try:
            await handler.handle(event, context)
            if isinstance(event, WorkflowReadyEvent):
                await self.phase_manager.notify_initialization_complete()
        except Exception as e:
            error_msg = f"Error handling '{type(event).__name__}' in workflow '{workflow_id}': {e}"
            logger.error(error_msg, exc_info=True)
            await self.phase_manager.notify_error_occurred(error_msg, traceback.format_exc())
