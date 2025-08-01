# file: autobyteus/autobyteus/workflow/phases/workflow_phase_manager.py
import logging
from typing import TYPE_CHECKING, Optional

from autobyteus.workflow.phases.workflow_operational_phase import WorkflowOperationalPhase

if TYPE_CHECKING:
    from autobyteus.workflow.context.workflow_context import WorkflowContext
    from autobyteus.workflow.streaming.workflow_event_notifier import WorkflowExternalEventNotifier

logger = logging.getLogger(__name__)

class WorkflowPhaseManager:
    """Manages the operational phase of a workflow."""
    def __init__(self, context: 'WorkflowContext', notifier: 'WorkflowExternalEventNotifier'):
        self.context = context
        self.notifier = notifier
        self.context.state.current_phase = WorkflowOperationalPhase.UNINITIALIZED
        logger.debug(f"WorkflowPhaseManager initialized for workflow '{context.workflow_id}'.")

    async def _transition_phase(self, new_phase: WorkflowOperationalPhase, extra_data: Optional[dict] = None):
        old_phase = self.context.state.current_phase
        if old_phase == new_phase:
            return
        logger.info(f"Workflow '{self.context.workflow_id}' transitioning from {old_phase.value} to {new_phase.value}.")
        self.context.state.current_phase = new_phase
        self.notifier.notify_phase_change(new_phase, old_phase, extra_data)

    async def notify_bootstrapping_started(self):
        await self._transition_phase(WorkflowOperationalPhase.BOOTSTRAPPING)

    async def notify_initialization_complete(self):
        await self._transition_phase(WorkflowOperationalPhase.IDLE)
        
    async def notify_processing_started(self):
        await self._transition_phase(WorkflowOperationalPhase.PROCESSING)

    async def notify_processing_complete_and_idle(self):
        await self._transition_phase(WorkflowOperationalPhase.IDLE)

    async def notify_error_occurred(self, error_message: str, error_details: Optional[str] = None):
        await self._transition_phase(WorkflowOperationalPhase.ERROR, {"error_message": error_message, "error_details": error_details})

    async def notify_shutdown_initiated(self):
        await self._transition_phase(WorkflowOperationalPhase.SHUTTING_DOWN)

    async def notify_final_shutdown_complete(self):
        await self._transition_phase(WorkflowOperationalPhase.SHUTDOWN_COMPLETE)
