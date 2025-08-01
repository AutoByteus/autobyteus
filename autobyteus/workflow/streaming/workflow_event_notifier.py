# file: autobyteus/autobyteus/workflow/streaming/workflow_event_notifier.py
import logging
from typing import Optional, Dict, Any, TYPE_CHECKING

from autobyteus.events.event_emitter import EventEmitter
from autobyteus.events.event_types import EventType
from autobyteus.workflow.phases.workflow_operational_phase import WorkflowOperationalPhase
from autobyteus.agent.streaming.stream_events import StreamEvent as AgentStreamEvent
from .workflow_stream_events import WorkflowStreamEvent, AgentEventRebroadcastPayload, WorkflowPhaseTransitionData, SubWorkflowEventRebroadcastPayload

if TYPE_CHECKING:
    from autobyteus.workflow.runtime.workflow_runtime import WorkflowRuntime
    from autobyteus.workflow.streaming.workflow_stream_events import WorkflowStreamEvent as WorkflowStreamEventTypeHint

logger = logging.getLogger(__name__)

class WorkflowExternalEventNotifier(EventEmitter):
    """
    Responsible for emitting unified WorkflowStreamEvents for consumption by
    external listeners (like a UI or the WorkflowEventStream).
    """
    def __init__(self, workflow_id: str, runtime_ref: 'WorkflowRuntime'):
        super().__init__()
        self.workflow_id = workflow_id
        self.runtime_ref = runtime_ref
        logger.debug(f"WorkflowExternalEventNotifier initialized for workflow '{self.workflow_id}'.")

    def _emit_event(self, event: 'WorkflowStreamEventTypeHint'):
        """
        Emits a fully-formed WorkflowStreamEvent.
        A new generic event type is used for the underlying pub/sub system to carry
        the unified event object.
        """
        self.emit(EventType.WORKFLOW_STREAM_EVENT, payload=event)

    def notify_phase_change(self, new_phase: WorkflowOperationalPhase, old_phase: Optional[WorkflowOperationalPhase], extra_data: Optional[Dict[str, Any]] = None):
        """
        Notifies of a workflow phase transition by creating and emitting a
        'WORKFLOW' sourced event.
        """
        payload_dict = {
            "new_phase": new_phase,
            "old_phase": old_phase,
            "error_message": extra_data.get("error_message") if extra_data else None,
        }
        filtered_payload_dict = {k: v for k, v in payload_dict.items() if v is not None}
        
        event = WorkflowStreamEvent(
            workflow_id=self.workflow_id,
            event_source_type="WORKFLOW",
            data=WorkflowPhaseTransitionData(**filtered_payload_dict)
        )
        self._emit_event(event)
    
    def publish_agent_event(self, agent_name: str, agent_event: AgentStreamEvent):
        """
        Wraps an event from a direct member agent and publishes it on the main workflow stream
        as an 'AGENT' sourced event.
        """
        event = WorkflowStreamEvent(
            workflow_id=self.workflow_id,
            event_source_type="AGENT",
            data=AgentEventRebroadcastPayload(
                agent_name=agent_name,
                agent_event=agent_event
            )
        )
        self._emit_event(event)
        
    def publish_sub_workflow_event(self, sub_workflow_node_name: str, sub_workflow_event: 'WorkflowStreamEventTypeHint'):
        """
        Wraps an event from a sub-workflow and publishes it on the parent workflow stream
        as a 'SUB_WORKFLOW' sourced event.
        """
        event = WorkflowStreamEvent(
            workflow_id=self.workflow_id,
            event_source_type="SUB_WORKFLOW",
            data=SubWorkflowEventRebroadcastPayload(
                sub_workflow_node_name=sub_workflow_node_name,
                sub_workflow_event=sub_workflow_event
            )
        )
        self._emit_event(event)
