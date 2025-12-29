import logging
from typing import TYPE_CHECKING, Optional

from autobyteus.agent_team.status.agent_team_status import AgentTeamStatus

if TYPE_CHECKING:
    from autobyteus.agent_team.context.agent_team_context import AgentTeamContext
    from autobyteus.agent_team.streaming.agent_team_event_notifier import AgentTeamExternalEventNotifier

logger = logging.getLogger(__name__)

class AgentTeamStatusManager:
    """Manages the operational status of an agent team."""
    def __init__(self, context: 'AgentTeamContext', notifier: 'AgentTeamExternalEventNotifier'):
        self.context = context
        self.notifier = notifier
        self.context.state.current_status = AgentTeamStatus.UNINITIALIZED
        logger.debug(f"AgentTeamStatusManager initialized for team '{context.team_id}'.")

    async def _transition_status(self, new_status: AgentTeamStatus, extra_data: Optional[dict] = None):
        old_status = self.context.state.current_status
        if old_status == new_status:
            return
        logger.info(f"Team '{self.context.team_id}' transitioning from {old_status.value} to {new_status.value}.")
        self.context.state.current_status = new_status
        self.notifier.notify_status_change(new_status, old_status, extra_data)

    async def notify_bootstrapping_started(self):
        await self._transition_status(AgentTeamStatus.BOOTSTRAPPING)

    async def notify_initialization_complete(self):
        await self._transition_status(AgentTeamStatus.IDLE)
        
    async def notify_processing_started(self):
        await self._transition_status(AgentTeamStatus.PROCESSING)

    async def notify_processing_complete_and_idle(self):
        await self._transition_status(AgentTeamStatus.IDLE)

    async def notify_error_occurred(self, error_message: str, error_details: Optional[str] = None):
        await self._transition_status(AgentTeamStatus.ERROR, {"error_message": error_message, "error_details": error_details})

    async def notify_shutdown_initiated(self):
        await self._transition_status(AgentTeamStatus.SHUTTING_DOWN)

    async def notify_final_shutdown_complete(self):
        await self._transition_status(AgentTeamStatus.SHUTDOWN_COMPLETE)
