# file: autobyteus/autobyteus/workflow/streaming/workflow_event_bridge.py
import asyncio
import logging
from typing import TYPE_CHECKING

from autobyteus.workflow.streaming.workflow_event_stream import WorkflowEventStream

if TYPE_CHECKING:
    from autobyteus.workflow.agentic_workflow import AgenticWorkflow
    from autobyteus.workflow.streaming.workflow_event_notifier import WorkflowExternalEventNotifier

logger = logging.getLogger(__name__)

class WorkflowEventBridge:
    """
    A dedicated component that bridges events from a sub-workflow's event stream
    to the parent workflow's notifier.
    """
    def __init__(self, sub_workflow: 'AgenticWorkflow', sub_workflow_node_name: str, parent_notifier: 'WorkflowExternalEventNotifier', loop: asyncio.AbstractEventLoop):
        self._sub_workflow = sub_workflow
        self._sub_workflow_node_name = sub_workflow_node_name
        self._parent_notifier = parent_notifier
        self._stream = WorkflowEventStream(sub_workflow)
        self._task: asyncio.Task = loop.create_task(self._run())
        logger.info(f"WorkflowEventBridge created and task started for sub-workflow '{sub_workflow_node_name}'.")

    async def _run(self):
        """The background task that consumes from the sub-workflow stream and re-publishes."""
        try:
            async for event in self._stream.all_events():
                # Re-broadcast the event to the parent, adding the sub-workflow context.
                self._parent_notifier.publish_sub_workflow_event(self._sub_workflow_node_name, event)
        except asyncio.CancelledError:
            logger.info(f"WorkflowEventBridge task for '{self._sub_workflow_node_name}' was cancelled.")
        except Exception as e:
            logger.error(f"Error in WorkflowEventBridge for '{self._sub_workflow_node_name}': {e}", exc_info=True)
        finally:
            logger.debug(f"WorkflowEventBridge task for '{self._sub_workflow_node_name}' is finishing.")

    async def cancel(self):
        """Gracefully stops the bridge."""
        logger.info(f"Cancelling WorkflowEventBridge for '{self._sub_workflow_node_name}'.")
        if not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass # Expected
        await self._stream.close()
        logger.info(f"WorkflowEventBridge for '{self._sub_workflow_node_name}' cancelled successfully.")
