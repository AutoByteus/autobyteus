import logging
from typing import TYPE_CHECKING, Optional

from autobyteus.agent_team.status.agent_team_status import AgentTeamStatus

if TYPE_CHECKING:
    from autobyteus.agent_team.context.agent_team_context import AgentTeamContext
    from autobyteus.agent_team.streaming.agent_team_event_notifier import AgentTeamExternalEventNotifier

logger = logging.getLogger(__name__)

class AgentTeamStatusManager:
    """
    Emits external notifications for status updates derived from events.
    The status itself is owned by the event stream projection.
    """
    def __init__(self, context: 'AgentTeamContext', notifier: 'AgentTeamExternalEventNotifier'):
        if notifier is None:
            raise ValueError("AgentTeamStatusManager requires a notifier.")
        self.context = context
        self.notifier = notifier
        if not isinstance(self.context.state.current_status, AgentTeamStatus):
            self.context.state.current_status = AgentTeamStatus.UNINITIALIZED
        logger.debug(f"AgentTeamStatusManager initialized for team '{context.team_id}'.")

    async def emit_status_update(self,
                                 old_status: AgentTeamStatus,
                                 new_status: AgentTeamStatus,
                                 additional_data: Optional[dict] = None) -> None:
        if old_status == new_status:
            return
        logger.info(f"Team '{self.context.team_id}' updating status from {old_status.value} to {new_status.value}.")
        self.notifier.notify_status_updated(new_status, old_status, additional_data)
