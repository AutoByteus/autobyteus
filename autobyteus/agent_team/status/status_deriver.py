# file: autobyteus/autobyteus/agent_team/status/status_deriver.py
import logging
from typing import Optional, Tuple, TYPE_CHECKING

from autobyteus.agent_team.status.agent_team_status import AgentTeamStatus
from autobyteus.agent_team.events.agent_team_events import (
    AgentTeamBootstrapStartedEvent,
    AgentTeamReadyEvent,
    AgentTeamIdleEvent,
    AgentTeamShutdownRequestedEvent,
    AgentTeamStoppedEvent,
    AgentTeamErrorEvent,
    OperationalAgentTeamEvent,
)

if TYPE_CHECKING:
    from autobyteus.agent_team.context.agent_team_context import AgentTeamContext
    from autobyteus.agent_team.events.agent_team_events import BaseAgentTeamEvent

logger = logging.getLogger(__name__)


class AgentTeamStatusDeriver:
    """
    Derives agent team status from an event stream.
    """
    def __init__(self, initial_status: AgentTeamStatus = AgentTeamStatus.UNINITIALIZED):
        self._current_status = initial_status
        logger.debug(f"AgentTeamStatusDeriver initialized with status '{initial_status.value}'.")

    @property
    def current_status(self) -> AgentTeamStatus:
        return self._current_status

    def apply(self, event: 'BaseAgentTeamEvent', context: Optional['AgentTeamContext'] = None) -> Tuple[AgentTeamStatus, AgentTeamStatus]:
        old_status = self._current_status
        new_status = self._reduce(event, old_status, context)
        self._current_status = new_status
        return old_status, new_status

    def _reduce(self, event: 'BaseAgentTeamEvent', current_status: AgentTeamStatus, context: Optional['AgentTeamContext']) -> AgentTeamStatus:
        if isinstance(event, AgentTeamBootstrapStartedEvent):
            return AgentTeamStatus.BOOTSTRAPPING
        if isinstance(event, AgentTeamReadyEvent):
            return AgentTeamStatus.IDLE
        if isinstance(event, AgentTeamIdleEvent):
            return AgentTeamStatus.IDLE
        if isinstance(event, AgentTeamShutdownRequestedEvent):
            if current_status == AgentTeamStatus.ERROR:
                return current_status
            return AgentTeamStatus.SHUTTING_DOWN
        if isinstance(event, AgentTeamStoppedEvent):
            if current_status == AgentTeamStatus.ERROR:
                return current_status
            return AgentTeamStatus.SHUTDOWN_COMPLETE
        if isinstance(event, AgentTeamErrorEvent):
            return AgentTeamStatus.ERROR

        if isinstance(event, OperationalAgentTeamEvent):
            return AgentTeamStatus.PROCESSING

        return current_status
