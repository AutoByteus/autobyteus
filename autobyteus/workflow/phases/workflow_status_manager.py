# file: autobyteus/autobyteus/workflow/phases/workflow_status_manager.py
import logging
from typing import TYPE_CHECKING, Optional

from autobyteus.workflow.phases.workflow_status import WorkflowStatus

if TYPE_CHECKING:
    from autobyteus.workflow.context.workflow_context import WorkflowContext
    from autobyteus.workflow.streaming.workflow_event_notifier import WorkflowExternalEventNotifier

logger = logging.getLogger(__name__)

class WorkflowStatusManager:
    """Manages the operational status of a workflow."""
    def __init__(self, context: 'WorkflowContext', notifier: 'WorkflowExternalEventNotifier'):
        self.context = context
        self.notifier = notifier
        self.context.state.current_status = WorkflowStatus.UNINITIALIZED
        logger.debug(f"WorkflowStatusManager initialized for workflow '{context.workflow_id}'.")

    async def _transition_status(self, new_status: WorkflowStatus, extra_data: Optional[dict] = None):
        old_status = self.context.state.current_status
        if old_status == new_status:
            return
        logger.info(f"Workflow '{self.context.workflow_id}' transitioning from {old_status.value} to {new_status.value}.")
        self.context.state.current_status = new_status
        self.notifier.notify_status_change(new_status, old_status, extra_data)

    async def notify_bootstrapping_started(self):
        await self._transition_status(WorkflowStatus.BOOTSTRAPPING)

    async def notify_initialization_complete(self):
        await self._transition_status(WorkflowStatus.IDLE)
        
    async def notify_processing_started(self):
        await self._transition_status(WorkflowStatus.PROCESSING)

    async def notify_processing_complete_and_idle(self):
        await self._transition_status(WorkflowStatus.IDLE)

    async def notify_error_occurred(self, error_message: str, error_details: Optional[str] = None):
        await self._transition_status(WorkflowStatus.ERROR, {"error_message": error_message, "error_details": error_details})

    async def notify_shutdown_initiated(self):
        await self._transition_status(WorkflowStatus.SHUTTING_DOWN)

    async def notify_final_shutdown_complete(self):
        await self._transition_status(WorkflowStatus.SHUTDOWN_COMPLETE)
