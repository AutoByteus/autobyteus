# file: autobyteus/autobyteus/workflow/streaming/workflow_event_notifier.py
import logging
from typing import Optional, Dict, Any, TYPE_CHECKING, Union

from autobyteus.events.event_emitter import EventEmitter
from autobyteus.events.event_types import EventType 
from autobyteus.workflow.phases.workflow_operational_phase import WorkflowOperationalPhase
from autobyteus.workflow.streaming.workflow_stream_events import WorkflowStreamEvent, WorkflowStreamEventType
from autobyteus.agent.streaming.stream_events import StreamEvent

if TYPE_CHECKING:
    from autobyteus.workflow.runtime.workflow_runtime import WorkflowRuntime

logger = logging.getLogger(__name__)

class WorkflowExternalEventNotifier(EventEmitter):
    """Responsible for emitting external events related to workflow phase and data."""
    def __init__(self, workflow_id: str, runtime_ref: 'WorkflowRuntime'):
        super().__init__()
        self.workflow_id = workflow_id
        self.runtime_ref = runtime_ref
        logger.debug(f"WorkflowExternalEventNotifier initialized for workflow '{self.workflow_id}'.")

    def _emit_workflow_event(self, event_type: WorkflowStreamEventType, data: Any):
        """
        Creates a WorkflowStreamEvent and emits it.
        The `data` is a dictionary that will be validated by the WorkflowStreamEvent model.
        """
        stream_event = WorkflowStreamEvent(
            workflow_id=self.workflow_id,
            event_type=event_type,
            data=data
        )
        # Using a generic EventType for the underlying emitter for internal pub/sub
        self.emit(EventType.AGENT_DATA_TOOL_LOG, payload=stream_event)

    def notify_phase_change(self, new_phase: WorkflowOperationalPhase, old_phase: WorkflowOperationalPhase, extra_data: Optional[Dict] = None):
        payload_data = {"new_phase": new_phase.value, "old_phase": old_phase.value if old_phase else None}
        if extra_data:
            payload_data.update(extra_data)
        self._emit_workflow_event(
            WorkflowStreamEventType.WORKFLOW_PHASE_TRANSITION,
            payload_data
        )

    def notify_agent_activity(self, agent_name: str, activity: Union[str, 'StreamEvent'], details: Optional[Any] = None):
        activity_str: str
        details_obj: Optional[Any] = details

        if isinstance(activity, StreamEvent):
            # If a full StreamEvent is passed, use its type as the activity and its data as details
            activity_str = f"Event: {activity.event_type.value}"
            details_obj = activity.data.model_dump()
        else:
            # Otherwise, use the activity as a simple string
            activity_str = str(activity)

        payload_data = {
            "agent_name": agent_name,
            "activity": activity_str,
            "details": details_obj
        }
        self._emit_workflow_event(
            WorkflowStreamEventType.AGENT_ACTIVITY_LOG,
            payload_data
        )

    def notify_final_result(self, result: Any):
        self._emit_workflow_event(
            WorkflowStreamEventType.WORKFLOW_FINAL_RESULT,
            {"result": result}
        )
