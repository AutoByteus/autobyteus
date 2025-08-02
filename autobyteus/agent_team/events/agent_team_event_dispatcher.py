# file: autobyteus/autobyteus/agent_team/events/agent_team_event_dispatcher.py
import logging
import traceback
from typing import TYPE_CHECKING

from autobyteus.agent_team.events.agent_team_events import BaseAgentTeamEvent, AgentTeamReadyEvent, ProcessUserMessageEvent

if TYPE_CHECKING:
    from autobyteus.agent_team.context.agent_team_context import AgentTeamContext
    from autobyteus.agent_team.handlers.agent_team_event_handler_registry import AgentTeamEventHandlerRegistry
    from autobyteus.agent_team.phases.agent_team_phase_manager import AgentTeamPhaseManager

logger = logging.getLogger(__name__)

class AgentTeamEventDispatcher:
    """Dispatches agent team events to their appropriate handlers."""

    def __init__(self,
                 event_handler_registry: 'AgentTeamEventHandlerRegistry',
                 phase_manager: 'AgentTeamPhaseManager'):
        self.registry = event_handler_registry
        self.phase_manager = phase_manager

    async def dispatch(self, event: BaseAgentTeamEvent, context: 'AgentTeamContext'):
        handler = self.registry.get_handler(type(event))
        team_id = context.team_id

        if not handler:
            logger.warning(f"Team '{team_id}': No handler for event '{type(event).__name__}'.")
            return

        try:
            await handler.handle(event, context)
            if isinstance(event, AgentTeamReadyEvent):
                await self.phase_manager.notify_initialization_complete()
        except Exception as e:
            error_msg = f"Error handling '{type(event).__name__}' in team '{team_id}': {e}"
            logger.error(error_msg, exc_info=True)
            await self.phase_manager.notify_error_occurred(error_msg, traceback.format_exc())
