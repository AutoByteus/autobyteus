# file: autobyteus/autobyteus/agent_team/handlers/lifecycle_agent_team_event_handler.py
import logging
from typing import TYPE_CHECKING

from autobyteus.agent_team.handlers.base_agent_team_event_handler import BaseAgentTeamEventHandler
from autobyteus.agent_team.events.agent_team_events import BaseAgentTeamEvent, AgentTeamReadyEvent, AgentTeamErrorEvent

if TYPE_CHECKING:
    from autobyteus.agent_team.context.agent_team_context import AgentTeamContext

logger = logging.getLogger(__name__)

class LifecycleAgentTeamEventHandler(BaseAgentTeamEventHandler):
    """Logs various lifecycle events for an agent team."""
    async def handle(self, event: BaseAgentTeamEvent, context: 'AgentTeamContext') -> None:
        team_id = context.team_id
        current_phase = context.state.current_phase.value

        if isinstance(event, AgentTeamReadyEvent):
            logger.info(f"Team '{team_id}' Logged AgentTeamReadyEvent. Current phase: {current_phase}")
        elif isinstance(event, AgentTeamErrorEvent):
            logger.error(
                f"Team '{team_id}' Logged AgentTeamErrorEvent: {event.error_message}. "
                f"Details: {event.exception_details}. Current phase: {current_phase}"
            )
        else:
            logger.warning(f"LifecycleAgentTeamEventHandler received unhandled event type: {type(event).__name__}")
