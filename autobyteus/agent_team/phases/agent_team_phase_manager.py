# file: autobyteus/autobyteus/agent_team/phases/agent_team_phase_manager.py
import logging
from typing import TYPE_CHECKING, Optional

from autobyteus.agent_team.phases.agent_team_operational_phase import AgentTeamOperationalPhase

if TYPE_CHECKING:
    from autobyteus.agent_team.context.agent_team_context import AgentTeamContext
    from autobyteus.agent_team.streaming.agent_team_event_notifier import AgentTeamExternalEventNotifier

logger = logging.getLogger(__name__)

class AgentTeamPhaseManager:
    """Manages the operational phase of an agent team."""
    def __init__(self, context: 'AgentTeamContext', notifier: 'AgentTeamExternalEventNotifier'):
        self.context = context
        self.notifier = notifier
        self.context.state.current_phase = AgentTeamOperationalPhase.UNINITIALIZED
        logger.debug(f"AgentTeamPhaseManager initialized for team '{context.team_id}'.")

    async def _transition_phase(self, new_phase: AgentTeamOperationalPhase, extra_data: Optional[dict] = None):
        old_phase = self.context.state.current_phase
        if old_phase == new_phase:
            return
        logger.info(f"Team '{self.context.team_id}' transitioning from {old_phase.value} to {new_phase.value}.")
        self.context.state.current_phase = new_phase
        self.notifier.notify_phase_change(new_phase, old_phase, extra_data)

    async def notify_bootstrapping_started(self):
        await self._transition_phase(AgentTeamOperationalPhase.BOOTSTRAPPING)

    async def notify_initialization_complete(self):
        await self._transition_phase(AgentTeamOperationalPhase.IDLE)
        
    async def notify_processing_started(self):
        await self._transition_phase(AgentTeamOperationalPhase.PROCESSING)

    async def notify_processing_complete_and_idle(self):
        await self._transition_phase(AgentTeamOperationalPhase.IDLE)

    async def notify_error_occurred(self, error_message: str, error_details: Optional[str] = None):
        await self._transition_phase(AgentTeamOperationalPhase.ERROR, {"error_message": error_message, "error_details": error_details})

    async def notify_shutdown_initiated(self):
        await self._transition_phase(AgentTeamOperationalPhase.SHUTTING_DOWN)

    async def notify_final_shutdown_complete(self):
        await self._transition_phase(AgentTeamOperationalPhase.SHUTDOWN_COMPLETE)
