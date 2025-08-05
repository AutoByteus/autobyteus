# file: autobyteus/autobyteus/agent_team/context/agent_team_runtime_state.py
import logging
from typing import List, Optional, TYPE_CHECKING, Dict

from autobyteus.agent_team.phases.agent_team_operational_phase import AgentTeamOperationalPhase
from autobyteus.agent.context import AgentConfig

if TYPE_CHECKING:
    from autobyteus.agent.agent import Agent
    from autobyteus.agent_team.events.agent_team_input_event_queue_manager import AgentTeamInputEventQueueManager
    from autobyteus.agent_team.phases.agent_team_phase_manager import AgentTeamPhaseManager
    from autobyteus.agent_team.context.team_node_config import TeamNodeConfig
    from autobyteus.agent_team.context.team_manager import TeamManager
    from autobyteus.agent_team.streaming.agent_event_multiplexer import AgentEventMultiplexer

logger = logging.getLogger(__name__)

class AgentTeamRuntimeState:
    """Encapsulates the dynamic, stateful data of a running agent team instance."""
    def __init__(self, team_id: str):
        if not team_id or not isinstance(team_id, str):
            raise ValueError("AgentTeamRuntimeState requires a non-empty string 'team_id'.")

        self.team_id: str = team_id
        self.current_phase: AgentTeamOperationalPhase = AgentTeamOperationalPhase.UNINITIALIZED
        
        # State populated by bootstrap steps
        self.prepared_coordinator_prompt: Optional[str] = None
        # REMOVED: self.node_alias_map and self.node_alias_to_config_map are no longer needed.

        # Core services
        self.team_manager: Optional['TeamManager'] = None

        # Runtime components and references
        self.input_event_queues: Optional['AgentTeamInputEventQueueManager'] = None
        self.phase_manager_ref: Optional['AgentTeamPhaseManager'] = None
        self.multiplexer_ref: Optional['AgentEventMultiplexer'] = None

        logger.info(f"AgentTeamRuntimeState initialized for team_id '{self.team_id}'.")

    @property
    def resolved_agent_configs(self) -> Optional[Dict[str, 'AgentConfig']]:
        """This property is now DEPRECATED as configs are resolved just-in-time."""
        logger.warning("'resolved_agent_configs' is deprecated. Node configs are resolved by TeamManager as needed.")
        return None

    def __repr__(self) -> str:
        agents_count = len(self.team_manager.get_all_agents()) if self.team_manager else 0
        coordinator_set = self.team_manager.coordinator_agent is not None if self.team_manager else False
        return (f"<AgentTeamRuntimeState id='{self.team_id}', phase='{self.current_phase.value}', "
                f"agents_count={agents_count}, coordinator_set={coordinator_set}, "
                f"team_manager_set={self.team_manager is not None}>")
