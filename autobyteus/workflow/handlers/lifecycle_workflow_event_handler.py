# file: autobyteus/autobyteus/workflow/handlers/lifecycle_workflow_event_handler.py
import logging
from typing import TYPE_CHECKING

from autobyteus.workflow.handlers.base_workflow_event_handler import BaseWorkflowEventHandler
from autobyteus.workflow.events.workflow_events import BaseWorkflowEvent, WorkflowReadyEvent, WorkflowErrorEvent

if TYPE_CHECKING:
    from autobyteus.workflow.context.workflow_context import WorkflowContext

logger = logging.getLogger(__name__)

class LifecycleWorkflowEventHandler(BaseWorkflowEventHandler):
    """Logs various lifecycle events for a workflow."""
    async def handle(self, event: BaseWorkflowEvent, context: 'WorkflowContext') -> None:
        workflow_id = context.workflow_id
        current_status = context.state.current_status.value

        if isinstance(event, WorkflowReadyEvent):
            logger.info(f"Workflow '{workflow_id}' Logged WorkflowReadyEvent. Current status: {current_status}")
        elif isinstance(event, WorkflowErrorEvent):
            logger.error(
                f"Workflow '{workflow_id}' Logged WorkflowErrorEvent: {event.error_message}. "
                f"Details: {event.exception_details}. Current status: {current_status}"
            )
        else:
            logger.warning(f"LifecycleWorkflowEventHandler received unhandled event type: {type(event).__name__}")
