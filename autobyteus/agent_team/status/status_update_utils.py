# file: autobyteus/autobyteus/agent_team/status/status_update_utils.py
import logging
from typing import Optional, Tuple, TYPE_CHECKING

from autobyteus.agent_team.status.agent_team_status import AgentTeamStatus
from autobyteus.agent_team.events.agent_team_events import AgentTeamErrorEvent

if TYPE_CHECKING:
    from autobyteus.agent_team.context.agent_team_context import AgentTeamContext
    from autobyteus.agent_team.events.agent_team_events import BaseAgentTeamEvent

logger = logging.getLogger(__name__)


def build_status_update_data(event: 'BaseAgentTeamEvent',
                             new_status: AgentTeamStatus) -> Optional[dict]:
    if new_status == AgentTeamStatus.ERROR and isinstance(event, AgentTeamErrorEvent):
        return {"error_message": event.error_message}
    return None


async def apply_event_and_derive_status(event: 'BaseAgentTeamEvent',
                                        context: 'AgentTeamContext') -> Tuple[AgentTeamStatus, AgentTeamStatus]:
    if context.state.event_store:
        try:
            context.state.event_store.append(event)
        except Exception as exc:  # pragma: no cover
            logger.error(f"Failed to append team event to store: {exc}", exc_info=True)

    if not context.state.status_deriver:
        return context.current_status, context.current_status

    old_status, new_status = context.state.status_deriver.apply(event, context)
    if old_status != new_status:
        context.current_status = new_status
        additional_data = build_status_update_data(event, new_status)
        if context.status_manager:
            await context.status_manager.emit_status_update(
                old_status, new_status, additional_data=additional_data
            )

    return old_status, new_status
