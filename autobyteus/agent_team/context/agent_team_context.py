# file: autobyteus/autobyteus/agent_team/context/agent_team_context.py
import logging
from typing import TYPE_CHECKING, List, Optional, Dict

if TYPE_CHECKING:
    from autobyteus.agent_team.context.agent_team_config import AgentTeamConfig
    from autobyteus.agent_team.context.agent_team_runtime_state import AgentTeamRuntimeState
    from autobyteus.agent.agent import Agent
    from autobyteus.agent_team.phases.agent_team_phase_manager import AgentTeamPhaseManager
    from autobyteus.agent_team.context.team_manager import TeamManager
    from autobyteus.agent_team.streaming.agent_event_multiplexer import AgentEventMultiplexer
    from autobyteus.agent.context import AgentConfig
    from autobyteus.agent_team.context.team_node_config import TeamNodeConfig

logger = logging.getLogger(__name__)

class AgentTeamContext:
    """Represents the complete operational context for a single agent team instance."""
    def __init__(self, team_id: str, config: 'AgentTeamConfig', state: 'AgentTeamRuntimeState'):
        if not team_id or not isinstance(team_id, str):
            raise ValueError("AgentTeamContext requires a non-empty string 'team_id'.")
        
        self.team_id: str = team_id
        self.config: 'AgentTeamConfig' = config
        self.state: 'AgentTeamRuntimeState' = state
        self._node_config_map: Optional[Dict[str, 'TeamNodeConfig']] = None
        
        logger.info(f"AgentTeamContext composed for team_id '{self.team_id}'.")

    def get_node_config_by_name(self, name: str) -> Optional['TeamNodeConfig']:
        """Efficiently retrieves a node's config by its friendly name."""
        if self._node_config_map is None:
            # Build cache on first access
            self._node_config_map = {node.name: node for node in self.config.nodes}
        return self._node_config_map.get(name)

    @property
    def agents(self) -> List['Agent']:
        """Returns all agents managed by the TeamManager."""
        if self.state.team_manager:
            return self.state.team_manager.get_all_agents()
        return []

    @property
    def coordinator_agent(self) -> Optional['Agent']:
        """Returns the coordinator agent from the TeamManager."""
        if self.state.team_manager:
            return self.state.team_manager.coordinator_agent
        return None

    @property
    def phase_manager(self) -> Optional['AgentTeamPhaseManager']:
        return self.state.phase_manager_ref

    @property
    def team_manager(self) -> Optional['TeamManager']:
        return self.state.team_manager
        
    @property
    def multiplexer(self) -> Optional['AgentEventMultiplexer']:
        return self.state.multiplexer_ref
