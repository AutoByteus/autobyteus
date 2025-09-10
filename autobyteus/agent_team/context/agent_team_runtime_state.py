# file: autobyteus/autobyteus/agent_team/context/agent_team_runtime_state.py
import logging
from typing import List, Optional, TYPE_CHECKING, Dict
from dataclasses import dataclass, field

from autobyteus.agent_team.phases.agent_team_operational_phase import AgentTeamOperationalPhase
from autobyteus.agent.context import AgentConfig

if TYPE_CHECKING:
    from autobyteus.agent.agent import Agent
    from autobyteus.agent_team.events.agent_team_input_event_queue_manager import AgentTeamInputEventQueueManager
    from autobyteus.agent_team.phases.agent_team_phase_manager import AgentTeamPhaseManager
    from autobyteus.agent_team.context.team_node_config import TeamNodeConfig
    from autobyteus.agent_team.context.team_manager import TeamManager
    from autobyteus.agent_team.streaming.agent_event_multiplexer import AgentEventMultiplexer
    from autobyteus.task_management.base_task_board import BaseTaskBoard
    from autobyteus.agent_team.task_notification.system_event_driven_agent_task_notifier import SystemEventDrivenAgentTaskNotifier

logger = logging.getLogger(__name__)

@dataclass
class AgentTeamRuntimeState:
    """Encapsulates the dynamic, stateful data of a running agent team instance."""
    team_id: str
    current_phase: AgentTeamOperationalPhase = AgentTeamOperationalPhase.UNINITIALIZED
    
    # State populated by bootstrap steps
    prepared_coordinator_prompt: Optional[str] = None
    final_agent_configs: Dict[str, 'AgentConfig'] = field(default_factory=dict)

    # Core services
    team_manager: Optional['TeamManager'] = None
    task_notifier: Optional['SystemEventDrivenAgentTaskNotifier'] = None

    # Runtime components and references
    input_event_queues: Optional['AgentTeamInputEventQueueManager'] = None
    phase_manager_ref: Optional['AgentTeamPhaseManager'] = None
    multiplexer_ref: Optional['AgentEventMultiplexer'] = None
    
    # Dynamic planning and artifact state
    task_board: Optional['BaseTaskBoard'] = None

    def __post_init__(self):
        if not self.team_id or not isinstance(self.team_id, str):
            raise ValueError("AgentTeamRuntimeState requires a non-empty string 'team_id'.")
        logger.info(f"AgentTeamRuntimeState initialized for team_id '{self.team_id}'.")

    def __repr__(self) -> str:
        agents_count = len(self.team_manager.get_all_agents()) if self.team_manager else 0
        coordinator_set = self.team_manager.coordinator_agent is not None if self.team_manager else False
        return (f"<AgentTeamRuntimeState id='{self.team_id}', phase='{self.current_phase.value}', "
                f"agents_count={agents_count}, coordinator_set={coordinator_set}, "
                f"final_configs_count={len(self.final_agent_configs)}, "
                f"team_manager_set={self.team_manager is not None}>")
