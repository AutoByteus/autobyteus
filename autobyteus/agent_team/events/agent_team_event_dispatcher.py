# file: autobyteus/autobyteus/agent_team/events/agent_team_event_dispatcher.py
import logging
import traceback
from typing import TYPE_CHECKING

from autobyteus.agent_team.events.agent_team_events import (
    BaseAgentTeamEvent,
    AgentTeamErrorEvent,
    AgentTeamIdleEvent,
    OperationalAgentTeamEvent,
)
from autobyteus.agent_team.status.status_update_utils import apply_event_and_derive_status

if TYPE_CHECKING:
    from autobyteus.agent_team.context.agent_team_context import AgentTeamContext
    from autobyteus.agent_team.handlers.agent_team_event_handler_registry import AgentTeamEventHandlerRegistry

logger = logging.getLogger(__name__)

class AgentTeamEventDispatcher:
    """Dispatches agent team events to their appropriate handlers."""

    def __init__(self,
                 event_handler_registry: 'AgentTeamEventHandlerRegistry'):
        self.registry = event_handler_registry

    async def dispatch(self, event: BaseAgentTeamEvent, context: 'AgentTeamContext'):
        team_id = context.team_id

        try:
            await apply_event_and_derive_status(event, context)
        except Exception as e:  # pragma: no cover
            logger.error(f"Team '{team_id}': Status derivation failed for '{type(event).__name__}': {e}", exc_info=True)

        handler = self.registry.get_handler(type(event))
        if not handler:
            logger.warning(f"Team '{team_id}': No handler for event '{type(event).__name__}'.")
            return

        try:
            await handler.handle(event, context)
        except Exception as e:
            error_msg = f"Error handling '{type(event).__name__}' in team '{team_id}': {e}"
            logger.error(error_msg, exc_info=True)
            if context.state.input_event_queues:
                await context.state.input_event_queues.enqueue_internal_system_event(
                    AgentTeamErrorEvent(error_message=error_msg, exception_details=traceback.format_exc())
                )
        else:
            if isinstance(event, OperationalAgentTeamEvent):
                if context.state.input_event_queues:
                    await context.state.input_event_queues.enqueue_internal_system_event(AgentTeamIdleEvent())
