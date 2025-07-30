# file: autobyteus/autobyteus/workflow/handlers/process_user_message_event_handler.py
import logging
from typing import TYPE_CHECKING
from autobyteus.workflow.handlers.base_workflow_event_handler import BaseWorkflowEventHandler
from autobyteus.workflow.events.workflow_events import ProcessUserMessageEvent

if TYPE_CHECKING:
    from autobyteus.workflow.context.workflow_context import WorkflowContext

logger = logging.getLogger(__name__)

class ProcessUserMessageEventHandler(BaseWorkflowEventHandler):
    """Handles user messages by routing them to the specified target agent."""
    async def handle(self, event: ProcessUserMessageEvent, context: 'WorkflowContext') -> None:
        await context.phase_manager.notify_processing_started()
        
        team_manager = context.team_manager
        if not team_manager:
            msg = f"Workflow '{context.workflow_id}': TeamManager not found. Cannot route message."
            logger.error(msg)
            await context.phase_manager.notify_error_occurred(msg, "TeamManager is not initialized.")
            return

        # TeamManager now ensures the agent is fully ready (created, started, idle).
        target_agent = await team_manager.ensure_agent_is_ready(event.target_agent_name)

        if not target_agent:
            msg = f"Workflow '{context.workflow_id}': Agent '{event.target_agent_name}' not found or failed to start. Cannot route message."
            logger.error(msg)
            await context.phase_manager.notify_error_occurred(msg, f"Agent '{event.target_agent_name}' not found or failed to start.")
            return

        await target_agent.post_user_message(event.user_message)
        logger.info(f"Workflow '{context.workflow_id}': Routed user message to agent '{event.target_agent_name}'.")
        await context.phase_manager.notify_processing_complete_and_idle()
