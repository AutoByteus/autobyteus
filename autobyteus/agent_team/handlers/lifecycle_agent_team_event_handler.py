# file: autobyteus/autobyteus/agent_team/handlers/lifecycle_agent_team_event_handler.py
import logging
from typing import TYPE_CHECKING

from autobyteus.agent_team.handlers.base_agent_team_event_handler import BaseAgentTeamEventHandler
from autobyteus.agent_team.events.agent_team_events import (
    BaseAgentTeamEvent,
    AgentTeamBootstrapStartedEvent,
    AgentTeamReadyEvent,
    AgentTeamIdleEvent,
    AgentTeamShutdownRequestedEvent,
    AgentTeamStoppedEvent,
    AgentTeamErrorEvent,
)

if TYPE_CHECKING:
    from autobyteus.agent_team.context.agent_team_context import AgentTeamContext

logger = logging.getLogger(__name__)

class LifecycleAgentTeamEventHandler(BaseAgentTeamEventHandler):
    """Logs various lifecycle events for an agent team."""
    async def handle(self, event: BaseAgentTeamEvent, context: 'AgentTeamContext') -> None:
        team_id = context.team_id
        current_status = context.state.current_status.value

        if isinstance(event, AgentTeamBootstrapStartedEvent):
            logger.info(f"Team '{team_id}' Logged AgentTeamBootstrapStartedEvent. Current status: {current_status}")
        elif isinstance(event, AgentTeamReadyEvent):
            logger.info(f"Team '{team_id}' Logged AgentTeamReadyEvent. Current status: {current_status}")
        elif isinstance(event, AgentTeamIdleEvent):
            logger.info(f"Team '{team_id}' Logged AgentTeamIdleEvent. Current status: {current_status}")
        elif isinstance(event, AgentTeamShutdownRequestedEvent):
            logger.info(f"Team '{team_id}' Logged AgentTeamShutdownRequestedEvent. Current status: {current_status}")
        elif isinstance(event, AgentTeamStoppedEvent):
            logger.info(f"Team '{team_id}' Logged AgentTeamStoppedEvent. Current status: {current_status}")
        elif isinstance(event, AgentTeamErrorEvent):
            logger.error(
                f"Team '{team_id}' Logged AgentTeamErrorEvent: {event.error_message}. "
                f"Details: {event.exception_details}. Current status: {current_status}"
            )
        else:
            logger.warning(f"LifecycleAgentTeamEventHandler received unhandled event type: {type(event).__name__}")
