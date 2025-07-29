# file: autobyteus/autobyteus/workflow/handlers/process_request_event_handler.py
import asyncio
import logging
from typing import TYPE_CHECKING, Any

from autobyteus.workflow.handlers.base_workflow_event_handler import BaseWorkflowEventHandler
from autobyteus.workflow.events.workflow_events import ProcessRequestEvent
from autobyteus.agent.streaming.agent_event_stream import AgentEventStream
from autobyteus.agent.streaming.stream_events import StreamEventType

if TYPE_CHECKING:
    from autobyteus.workflow.context.workflow_context import WorkflowContext

logger = logging.getLogger(__name__)

class ProcessRequestEventHandler(BaseWorkflowEventHandler):
    """
    Handles the initial user request, starts the coordinator, and streams
    its activity back through the workflow's notifier.
    """
    async def handle(self, event: ProcessRequestEvent, context: 'WorkflowContext') -> None:
        workflow_id = context.workflow_id
        phase_manager = context.phase_manager
        notifier = phase_manager.notifier
        
        await phase_manager.notify_processing_started()
        logger.info(f"Workflow '{workflow_id}': Handling ProcessRequestEvent.")
        
        # Get the coordinator from the context, which delegates to TeamManager.
        coordinator = context.coordinator_agent
        if not coordinator:
            msg = "Coordinator agent not found. Cannot process request."
            logger.error(f"Workflow '{workflow_id}': {msg}")
            await phase_manager.notify_error_occurred(msg, "")
            return

        notifier.notify_agent_activity(coordinator.context.config.name, "Task Assigned", event.user_message.content)
            
        if not coordinator.is_running:
            logger.info(f"Workflow '{workflow_id}': Coordinator is not running. Starting it now.")
            try:
                coordinator.start()
                await asyncio.sleep(0.1) # Allow thread to start
            except Exception as e:
                msg = f"Failed to start coordinator: {e}"
                logger.error(msg, exc_info=True)
                await phase_manager.notify_error_occurred(msg, str(e))
                return

        streamer = None
        try:
            streamer = AgentEventStream(coordinator)
            await coordinator.post_user_message(event.user_message)
            
            final_result: Any = None
            async for agent_event in streamer.all_events():
                # Rebroadcast every event from the coordinator as an AGENT_ACTIVITY_LOG
                notifier.notify_agent_activity(coordinator.context.config.name, agent_event)
                if agent_event.event_type == StreamEventType.ASSISTANT_COMPLETE_RESPONSE:
                    final_result = agent_event.data.content

            logger.info(f"Workflow '{workflow_id}' processing complete. Final result captured.")
            notifier.notify_final_result(final_result)
            
        except Exception as e:
            msg = f"An error occurred while streaming coordinator activity: {e}"
            logger.error(f"Workflow '{workflow_id}': {msg}", exc_info=True)
            await phase_manager.notify_error_occurred(msg, str(e))
        finally:
            if streamer: await streamer.close()
            await phase_manager.notify_processing_complete_and_idle()
