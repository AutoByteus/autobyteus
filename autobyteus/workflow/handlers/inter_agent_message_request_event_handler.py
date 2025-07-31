# file: autobyteus/autobyteus/workflow/handlers/inter_agent_message_request_event_handler.py
import logging
from typing import TYPE_CHECKING

from autobyteus.workflow.handlers.base_workflow_event_handler import BaseWorkflowEventHandler
from autobyteus.workflow.events.workflow_events import InterAgentMessageRequestEvent
from autobyteus.agent.message.inter_agent_message import InterAgentMessage
from autobyteus.agent.message.agent_input_user_message import AgentInputUserMessage
from autobyteus.workflow.agentic_workflow import AgenticWorkflow
from autobyteus.agent.agent import Agent

if TYPE_CHECKING:
    from autobyteus.workflow.context.workflow_context import WorkflowContext

logger = logging.getLogger(__name__)

class InterAgentMessageRequestEventHandler(BaseWorkflowEventHandler):
    """
    Handles requests to send messages between nodes (agents or sub-workflows).
    It relies on the TeamManager to handle on-demand startup of the recipient.
    """
    async def handle(self, event: InterAgentMessageRequestEvent, context: 'WorkflowContext') -> None:
        workflow_id = context.workflow_id
        team_manager = context.team_manager
        
        if not team_manager:
            logger.error(f"Workflow '{workflow_id}': TeamManager not found. Cannot route message from '{event.sender_agent_id}' to '{event.recipient_name}'.")
            return

        try:
            target_node = await team_manager.ensure_node_is_ready(event.recipient_name)
        except Exception as e:
            msg = f"Recipient node '{event.recipient_name}' not found or failed to start for message from '{event.sender_agent_id}'. Error: {e}"
            logger.error(f"Workflow '{workflow_id}': {msg}", exc_info=True)
            return

        try:
            if isinstance(target_node, AgenticWorkflow):
                # If target is a sub-workflow, post a user message to it.
                # The sub-workflow will route it to its own coordinator.
                message_for_workflow = AgentInputUserMessage(content=event.content)
                await target_node.post_message(message_for_workflow)
                logger.info(f"Workflow '{workflow_id}': Successfully posted message from '{event.sender_agent_id}' to sub-workflow '{event.recipient_name}'.")
            
            elif isinstance(target_node, Agent):
                # If target is a regular agent, create and post an InterAgentMessage.
                message_for_agent = InterAgentMessage.create_with_dynamic_message_type(
                    recipient_role_name=target_node.context.config.role,
                    recipient_agent_id=target_node.agent_id,
                    content=event.content,
                    message_type=event.message_type,
                    sender_agent_id=event.sender_agent_id
                )
                await target_node.post_inter_agent_message(message_for_agent)
                logger.info(f"Workflow '{workflow_id}': Successfully posted message from '{event.sender_agent_id}' to agent '{event.recipient_name}'.")
            else:
                raise TypeError(f"Target node '{event.recipient_name}' is of an unsupported type: {type(target_node).__name__}")
        
        except Exception as e:
            msg = f"Error posting message to node '{event.recipient_name}': {e}"
            logger.error(f"Workflow '{workflow_id}': {msg}", exc_info=True)
