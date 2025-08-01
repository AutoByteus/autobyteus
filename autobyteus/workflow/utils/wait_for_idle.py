# file: autobyteus/autobyteus/workflow/utils/wait_for_idle.py
import asyncio
import logging
from typing import TYPE_CHECKING

from autobyteus.workflow.streaming.workflow_event_stream import WorkflowEventStream
from autobyteus.workflow.phases.workflow_operational_phase import WorkflowOperationalPhase

if TYPE_CHECKING:
    from autobyteus.workflow.agentic_workflow import AgenticWorkflow

logger = logging.getLogger(__name__)

async def _wait_loop(streamer: WorkflowEventStream, workflow_id: str):
    """Internal helper to listen for the IDLE or ERROR event."""
    async for event in streamer.all_events():
        if event.event_source_type == "WORKFLOW" and event.data.new_phase == WorkflowOperationalPhase.IDLE:
            logger.info(f"Workflow '{workflow_id}' has become idle.")
            return
        if event.event_source_type == "WORKFLOW" and event.data.new_phase == WorkflowOperationalPhase.ERROR:
             error_message = f"Workflow '{workflow_id}' entered an error state while waiting for idle: {event.data.error_message}"
             logger.error(error_message)
             raise RuntimeError(error_message)

async def wait_for_workflow_to_be_idle(workflow: 'AgenticWorkflow', timeout: float = 60.0):
    """
    Waits for a workflow to complete its bootstrapping and enter the IDLE state.

    Args:
        workflow: The workflow instance to monitor.
        timeout: The maximum time in seconds to wait.

    Raises:
        asyncio.TimeoutError: If the workflow does not become idle within the timeout period.
        RuntimeError: If the workflow enters an error state.
    """
    if workflow.get_current_phase() == WorkflowOperationalPhase.IDLE:
        return
    
    logger.info(f"Waiting for workflow '{workflow.workflow_id}' to become idle (timeout: {timeout}s)...")
    
    streamer = WorkflowEventStream(workflow)
    try:
        await asyncio.wait_for(_wait_loop(streamer, workflow.workflow_id), timeout=timeout)
    finally:
        await streamer.close()
