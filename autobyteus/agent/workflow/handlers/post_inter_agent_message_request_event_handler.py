# file: autobyteus/autobyteus/agent/workflow/handlers/post_inter_agent_message_request_event_handler.py
import logging
from typing import TYPE_CHECKING, Any

from .base_workflow_event_handler import BaseWorkflowEventHandler
from ..events.workflow_events import PostInterAgentMessageRequestEvent
from ....agent.message.inter_agent_message import InterAgentMessage
from ....agent.utils.wait_for_idle import wait_for_agent_to_be_idle
from ....agent.streaming.agent_event_stream import AgentEventStream
from ....agent.streaming.stream_events import StreamEventType

if TYPE_CHECKING:
    from ..workflow_context import WorkflowContext

logger = logging.getLogger(__name__)

class PostInterAgentMessageRequestEventHandler(BaseWorkflowEventHandler):
    """
    Handles requests to send messages between agents, orchestrating on-demand
    startup and streaming the sub-task's activity.
    """
    async def handle(self, event: PostInterAgentMessageRequestEvent, context: 'WorkflowContext') -> None:
        workflow_id = context.workflow_id
        notifier = context.phase_manager.notifier
        
        sender = next((a for a in context.agents if a.agent_id == event.sender_agent_id), None)
        if not sender:
            logger.error(f"Workflow '{workflow_id}': Could not find sender agent '{event.sender_agent_id}'.")
            return

        team_context = sender.context.custom_data.get('team_context')
        target_agent = team_context.get_agent_by_friendly_name(event.recipient_name)
        
        if not target_agent:
            msg = f"Recipient agent '{event.recipient_name}' not found."
            logger.error(f"Workflow '{workflow_id}': {msg}")
            notifier.notify_agent_activity(event.recipient_name, "Error", msg)
            return

        # --- On-Demand Startup ---
        if not target_agent.is_running:
            notifier.notify_agent_activity(event.recipient_name, "Starting on-demand")
            try:
                target_agent.start()
                await wait_for_agent_to_be_idle(target_agent, timeout=60.0)
                notifier.notify_agent_activity(event.recipient_name, "Started and Idle")
            except Exception as e:
                msg = f"Failed to start agent '{event.recipient_name}': {e}"
                logger.error(f"Workflow '{workflow_id}': {msg}", exc_info=True)
                notifier.notify_agent_activity(event.recipient_name, "Startup Failed", str(e))
                return
        
        # --- Stream Sub-Task Activity ---
        streamer = None
        try:
            streamer = AgentEventStream(target_agent)
            message = InterAgentMessage.create_with_dynamic_message_type(
                recipient_role_name=target_agent.context.config.role,
                recipient_agent_id=target_agent.agent_id,
                content=event.content, message_type=event.message_type,
                sender_agent_id=event.sender_agent_id
            )
            await target_agent.post_inter_agent_message(message)
            
            final_result: Any = None
            async for agent_event in streamer.all_events():
                notifier.notify_agent_activity(event.recipient_name, agent_event)
                if agent_event.event_type == StreamEventType.ASSISTANT_COMPLETE_RESPONSE:
                    final_result = agent_event.data.content

            # Send the result back to the original sender (the coordinator)
            result_message = InterAgentMessage(
                recipient_role_name=sender.context.config.role,
                recipient_agent_id=sender.agent_id,
                content=f"Task completed by {event.recipient_name}. Result: {final_result}",
                message_type="task_result",
                sender_agent_id=target_agent.agent_id
            )
            await sender.post_inter_agent_message(result_message)
            notifier.notify_agent_activity(event.recipient_name, "Task Completed")

        except Exception as e:
            msg = f"Error during sub-task execution for '{event.recipient_name}': {e}"
            logger.error(f"Workflow '{workflow_id}': {msg}", exc_info=True)
            notifier.notify_agent_activity(event.recipient_name, "Execution Error", str(e))
        finally:
            if streamer: await streamer.close()
