# file: autobyteus/autobyteus/agent_team/handlers/tool_approval_team_event_handler.py
import logging
from typing import TYPE_CHECKING

from autobyteus.agent_team.handlers.base_agent_team_event_handler import BaseAgentTeamEventHandler
from autobyteus.agent_team.events.agent_team_events import ToolApprovalTeamEvent

if TYPE_CHECKING:
    from autobyteus.agent_team.context.agent_team_context import AgentTeamContext

logger = logging.getLogger(__name__)

class ToolApprovalTeamEventHandler(BaseAgentTeamEventHandler):
    """
    Handles tool approval events by routing them to the correct agent.
    """
    async def handle(self, event: ToolApprovalTeamEvent, context: 'AgentTeamContext') -> None:
        team_id = context.team_id
        team_manager = context.team_manager

        if not team_manager:
            msg = f"Team '{team_id}': TeamManager not found. Cannot route approval for agent '{event.agent_name}'."
            logger.error(msg)
            await context.phase_manager.notify_error_occurred(msg, "TeamManager is not initialized.")
            return

        from autobyteus.agent.agent import Agent
        target_node = await team_manager.ensure_node_is_ready(name_or_agent_id=event.agent_name)
        if not isinstance(target_node, Agent):
            msg = f"Team '{team_id}': Target node '{event.agent_name}' for approval is not an agent."
            logger.error(msg)
            await context.phase_manager.notify_error_occurred(msg, f"Node '{event.agent_name}' is not an agent.")
            return
        
        target_agent = target_node

        if not target_agent:
            msg = f"Team '{team_id}': Target agent '{event.agent_name}' for approval not found or failed to start."
            logger.error(msg)
            await context.phase_manager.notify_error_occurred(msg, f"Agent '{event.agent_name}' not found or failed to start.")
            return

        logger.info(f"Team '{team_id}': Posting tool approval (Approved: {event.is_approved}) to agent '{event.agent_name}' for invocation '{event.tool_invocation_id}'.")
        await target_agent.post_tool_execution_approval(
            tool_invocation_id=event.tool_invocation_id,
            is_approved=event.is_approved,
            reason=event.reason
        )
