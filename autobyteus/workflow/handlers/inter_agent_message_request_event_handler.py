# file: autobyteus/autobyteus/workflow/handlers/inter_agent_message_request_event_handler.py
import logging
from typing import TYPE_CHECKING

from autobyteus.workflow.handlers.base_workflow_event_handler import BaseWorkflowEventHandler
from autobyteus.workflow.events.workflow_events import InterAgentMessageRequestEvent
from autobyteus.agent.message.inter_agent_message import InterAgentMessage

if TYPE_CHECKING:
    from autobyteus.workflow.context.workflow_context import WorkflowContext

logger = logging.getLogger(__name__)

class InterAgentMessageRequestEventHandler(BaseWorkflowEventHandler):
    """
    Handles requests to send messages between agents. It relies on the TeamManager
    to handle on-demand startup of the recipient agent.
    """
    async def handle(self, event: InterAgentMessageRequestEvent, context: 'WorkflowContext') -> None:
        workflow_id = context.workflow_id
        team_manager = context.team_manager
        
        if not team_manager:
            logger.error(f"Workflow '{workflow_id}': TeamManager not found. Cannot route message from '{event.sender_agent_id}' to '{event.recipient_name}'.")
            return

        # TeamManager now ensures the agent is fully ready (created, started, idle).
        target_agent = await team_manager.ensure_agent_is_ready(event.recipient_name)
        
        if not target_agent:
            msg = f"Recipient agent '{event.recipient_name}' not found or failed to start for message from '{event.sender_agent_id}'."
            logger.error(f"Workflow '{workflow_id}': {msg}")
            # In the future, we might want to send an error message back to the sender.
            return

        # --- Post Message ---
        try:
            message = InterAgentMessage.create_with_dynamic_message_type(
                recipient_role_name=target_agent.context.config.role,
                recipient_agent_id=target_agent.agent_id,
                content=event.content,
                message_type=event.message_type,
                sender_agent_id=event.sender_agent_id
            )
            await target_agent.post_inter_agent_message(message)
            logger.info(f"Workflow '{workflow_id}': Successfully posted message from '{event.sender_agent_id}' to '{event.recipient_name}'.")
        except Exception as e:
            msg = f"Error posting inter-agent message to '{event.recipient_name}': {e}"
            logger.error(f"Workflow '{workflow_id}': {msg}", exc_info=True)
