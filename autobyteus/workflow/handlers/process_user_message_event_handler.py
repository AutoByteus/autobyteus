# file: autobyteus/autobyteus/workflow/handlers/process_user_message_event_handler.py
import logging
from typing import TYPE_CHECKING
from autobyteus.workflow.handlers.base_workflow_event_handler import BaseWorkflowEventHandler
from autobyteus.workflow.events.workflow_events import ProcessUserMessageEvent
from autobyteus.agent.agent import Agent
from autobyteus.workflow.agentic_workflow import AgenticWorkflow
from autobyteus.agent.message.agent_input_user_message import AgentInputUserMessage

if TYPE_CHECKING:
    from autobyteus.workflow.context.workflow_context import WorkflowContext

logger = logging.getLogger(__name__)

class ProcessUserMessageEventHandler(BaseWorkflowEventHandler):
    """Handles user messages by routing them to the specified target agent or sub-workflow."""
    async def handle(self, event: ProcessUserMessageEvent, context: 'WorkflowContext') -> None:
        await context.phase_manager.notify_processing_started()
        
        team_manager = context.team_manager
        if not team_manager:
            msg = f"Workflow '{context.workflow_id}': TeamManager not found. Cannot route message."
            logger.error(msg)
            await context.phase_manager.notify_error_occurred(msg, "TeamManager is not initialized.")
            return

        try:
            target_node = await team_manager.ensure_node_is_ready(event.target_agent_name)
        except Exception as e:
            msg = f"Workflow '{context.workflow_id}': Node '{event.target_agent_name}' not found or failed to start. Cannot route message. Error: {e}"
            logger.error(msg, exc_info=True)
            await context.phase_manager.notify_error_occurred(msg, f"Node '{event.target_agent_name}' not found or failed to start.")
            return

        if isinstance(target_node, Agent):
            await target_node.post_user_message(event.user_message)
            logger.info(f"Workflow '{context.workflow_id}': Routed user message to agent node '{event.target_agent_name}'.")
        elif isinstance(target_node, AgenticWorkflow):
            await target_node.post_message(event.user_message)
            logger.info(f"Workflow '{context.workflow_id}': Routed user message to sub-workflow node '{event.target_agent_name}'.")
        else:
            msg = f"Target node '{event.target_agent_name}' is of an unsupported type: {type(target_node).__name__}"
            logger.error(f"Workflow '{context.workflow_id}': {msg}")
            await context.phase_manager.notify_error_occurred(msg, "")

        await context.phase_manager.notify_processing_complete_and_idle()
