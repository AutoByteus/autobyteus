# file: autobyteus/autobyteus/agent_team/factory/agent_team_factory.py
import logging
import uuid
from typing import Optional, Dict, List

from autobyteus.utils.singleton import SingletonMeta
from autobyteus.agent_team.agent_team import AgentTeam
from autobyteus.agent_team.context.agent_team_config import AgentTeamConfig
from autobyteus.agent_team.context.agent_team_context import AgentTeamContext
from autobyteus.agent_team.context.agent_team_runtime_state import AgentTeamRuntimeState
from autobyteus.agent_team.context.team_manager import TeamManager
from autobyteus.agent_team.runtime.agent_team_runtime import AgentTeamRuntime
from autobyteus.agent_team.handlers.agent_team_event_handler_registry import AgentTeamEventHandlerRegistry
from autobyteus.agent_team.handlers.process_user_message_event_handler import ProcessUserMessageEventHandler
from autobyteus.agent_team.handlers.lifecycle_agent_team_event_handler import LifecycleAgentTeamEventHandler
from autobyteus.agent_team.handlers.inter_agent_message_request_event_handler import InterAgentMessageRequestEventHandler
from autobyteus.agent_team.handlers.tool_approval_team_event_handler import ToolApprovalTeamEventHandler
from autobyteus.agent_team.events.agent_team_events import (
    ProcessUserMessageEvent,
    AgentTeamReadyEvent,
    AgentTeamErrorEvent,
    InterAgentMessageRequestEvent,
    ToolApprovalTeamEvent
)

logger = logging.getLogger(__name__)

class AgentTeamFactory(metaclass=SingletonMeta):
    """
    A singleton factory for creating and managing AgentTeam instances.
    It orchestrates the assembly of all core agent team components.
    """
    def __init__(self):
        self._active_teams: Dict[str, AgentTeam] = {}
        logger.info("AgentTeamFactory (Singleton) initialized.")

    def _get_default_event_handler_registry(self) -> AgentTeamEventHandlerRegistry:
        """Returns a registry with default handlers for a new agent team."""
        registry = AgentTeamEventHandlerRegistry()
        registry.register(ProcessUserMessageEvent, ProcessUserMessageEventHandler())
        registry.register(InterAgentMessageRequestEvent, InterAgentMessageRequestEventHandler())
        registry.register(ToolApprovalTeamEvent, ToolApprovalTeamEventHandler())
        lifecycle_handler = LifecycleAgentTeamEventHandler()
        registry.register(AgentTeamReadyEvent, lifecycle_handler)
        registry.register(AgentTeamErrorEvent, lifecycle_handler)
        return registry

    def create_team(self, config: AgentTeamConfig) -> AgentTeam:
        """
        Creates a new agent team based on the provided AgentTeamConfig, stores it,
        and returns its facade (AgentTeam).
        """
        if not isinstance(config, AgentTeamConfig):
            raise TypeError(f"Expected AgentTeamConfig instance, got {type(config).__name__}.")

        team_id = f"team_{uuid.uuid4().hex[:8]}"
        while team_id in self._active_teams:
            team_id = f"team_{uuid.uuid4().hex[:8]}"

        # --- Component Assembly as per new architecture ---
        state = AgentTeamRuntimeState(team_id=team_id)
        context = AgentTeamContext(team_id=team_id, config=config, state=state)
        
        handler_registry = self._get_default_event_handler_registry()
        runtime = AgentTeamRuntime(context=context, event_handler_registry=handler_registry)
        
        team_manager = TeamManager(
            team_id=team_id,
            runtime=runtime,
            multiplexer=runtime.multiplexer # Pass multiplexer created in runtime
        )
        
        context.state.team_manager = team_manager
        
        team = AgentTeam(runtime=runtime)
        
        self._active_teams[team_id] = team
        logger.info(f"Agent Team '{team_id}' created and stored successfully.")
        return team

    def get_team(self, team_id: str) -> Optional[AgentTeam]:
        """Retrieves an active agent team instance by its ID."""
        return self._active_teams.get(team_id)

    async def remove_team(self, team_id: str, shutdown_timeout: float = 10.0) -> bool:
        """
        Removes an agent team from the factory's management and gracefully stops it.
        """
        team = self._active_teams.pop(team_id, None)
        if team:
            logger.info(f"Removing agent team '{team_id}'. Attempting graceful shutdown.")
            await team.stop(timeout=shutdown_timeout)
            return True
        logger.warning(f"Agent team with ID '{team_id}' not found for removal.")
        return False

    def list_active_team_ids(self) -> List[str]:
        """Returns a list of IDs of all active agent teams managed by this factory."""
        return list(self._active_teams.keys())
