# file: autobyteus/autobyteus/workflow/handlers/tool_approval_workflow_event_handler.py
import logging
from typing import TYPE_CHECKING

from autobyteus.workflow.handlers.base_workflow_event_handler import BaseWorkflowEventHandler
from autobyteus.workflow.events.workflow_events import ToolApprovalWorkflowEvent

if TYPE_CHECKING:
    from autobyteus.workflow.context.workflow_context import WorkflowContext

logger = logging.getLogger(__name__)

class ToolApprovalWorkflowEventHandler(BaseWorkflowEventHandler):
    """
    Handles tool approval events by routing them to the correct agent.
    """
    async def handle(self, event: ToolApprovalWorkflowEvent, context: 'WorkflowContext') -> None:
        workflow_id = context.workflow_id
        team_manager = context.team_manager

        if not team_manager:
            msg = f"Workflow '{workflow_id}': TeamManager not found. Cannot route approval for agent '{event.agent_name}'."
            logger.error(msg)
            await context.phase_manager.notify_error_occurred(msg, "TeamManager is not initialized.")
            return

        target_agent = await team_manager.ensure_agent_is_ready(event.agent_name)
        if not target_agent:
            msg = f"Workflow '{workflow_id}': Target agent '{event.agent_name}' for approval not found or failed to start."
            logger.error(msg)
            await context.phase_manager.notify_error_occurred(msg, f"Agent '{event.agent_name}' not found or failed to start.")
            return

        logger.info(f"Workflow '{workflow_id}': Posting tool approval (Approved: {event.is_approved}) to agent '{event.agent_name}' for invocation '{event.tool_invocation_id}'.")
        await target_agent.post_tool_execution_approval(
            tool_invocation_id=event.tool_invocation_id,
            is_approved=event.is_approved,
            reason=event.reason
        )
