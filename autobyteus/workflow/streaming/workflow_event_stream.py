# file: autobyteus/autobyteus/workflow/streaming/workflow_event_stream.py
import asyncio
import queue
from typing import AsyncIterator, TYPE_CHECKING

from autobyteus.events.event_types import EventType
from autobyteus.workflow.streaming.workflow_stream_events import WorkflowStreamEvent
from autobyteus.agent.streaming.queue_streamer import stream_queue_items

if TYPE_CHECKING:
    from autobyteus.workflow.agentic_workflow import AgenticWorkflow

_SENTINEL = object()

class WorkflowEventStream:
    """Consumes events from a WorkflowExternalEventNotifier for a specific workflow."""
    def __init__(self, workflow: 'AgenticWorkflow'):
        self.workflow_id = workflow.workflow_id
        self._internal_q = queue.Queue()
        self._notifier = workflow._runtime.notifier
        self._notifier.subscribe(EventType.WORKFLOW_STREAM_EVENT, self._handle_event)

    def _handle_event(self, payload: WorkflowStreamEvent, **kwargs):
        if isinstance(payload, WorkflowStreamEvent) and payload.workflow_id == self.workflow_id:
            self._internal_q.put(payload)

    async def close(self):
        self._notifier.unsubscribe(EventType.WORKFLOW_STREAM_EVENT, self._handle_event)
        await asyncio.get_running_loop().run_in_executor(None, self._internal_q.put, _SENTINEL)

    def all_events(self) -> AsyncIterator[WorkflowStreamEvent]:
        """The primary method to consume all structured events from the workflow."""
        return stream_queue_items(self._internal_q, _SENTINEL, f"workflow_{self.workflow_id}_stream")
