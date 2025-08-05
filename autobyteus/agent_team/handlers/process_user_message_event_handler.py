# file: autobyteus/autobyteus/agent_team/handlers/process_user_message_event_handler.py
import logging
from typing import TYPE_CHECKING
from autobyteus.agent_team.handlers.base_agent_team_event_handler import BaseAgentTeamEventHandler
from autobyteus.agent_team.events.agent_team_events import ProcessUserMessageEvent
from autobyteus.agent.agent import Agent
from autobyteus.agent_team.agent_team import AgentTeam
from autobyteus.agent.message.agent_input_user_message import AgentInputUserMessage

if TYPE_CHECKING:
    from autobyteus.agent_team.context.agent_team_context import AgentTeamContext

logger = logging.getLogger(__name__)

class ProcessUserMessageEventHandler(BaseAgentTeamEventHandler):
    """Handles user messages by routing them to the specified target agent or sub-team."""
    async def handle(self, event: ProcessUserMessageEvent, context: 'AgentTeamContext') -> None:
        await context.phase_manager.notify_processing_started()
        
        team_manager = context.team_manager
        if not team_manager:
            msg = f"Team '{context.team_id}': TeamManager not found. Cannot route message."
            logger.error(msg)
            await context.phase_manager.notify_error_occurred(msg, "TeamManager is not initialized.")
            return

        try:
            target_node = await team_manager.ensure_node_is_ready(name_or_agent_id=event.target_agent_name)
        except Exception as e:
            msg = f"Team '{context.team_id}': Node '{event.target_agent_name}' not found or failed to start. Cannot route message. Error: {e}"
            logger.error(msg, exc_info=True)
            await context.phase_manager.notify_error_occurred(msg, f"Node '{event.target_agent_name}' not found or failed to start.")
            return

        if isinstance(target_node, Agent):
            await target_node.post_user_message(event.user_message)
            logger.info(f"Team '{context.team_id}': Routed user message to agent node '{event.target_agent_name}'.")
        elif isinstance(target_node, AgentTeam):
            await target_node.post_message(event.user_message)
            logger.info(f"Team '{context.team_id}': Routed user message to sub-team node '{event.target_agent_name}'.")
        else:
            msg = f"Target node '{event.target_agent_name}' is of an unsupported type: {type(target_node).__name__}"
            logger.error(f"Team '{context.team_id}': {msg}")
            await context.phase_manager.notify_error_occurred(msg, "")

        await context.phase_manager.notify_processing_complete_and_idle()
