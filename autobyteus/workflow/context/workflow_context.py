# file: autobyteus/autobyteus/workflow/context/workflow_context.py
import logging
from typing import TYPE_CHECKING, List, Optional, Dict

if TYPE_CHECKING:
    from autobyteus.workflow.context.workflow_config import WorkflowConfig
    from autobyteus.workflow.context.workflow_runtime_state import WorkflowRuntimeState
    from autobyteus.agent.agent import Agent
    from autobyteus.workflow.phases.workflow_phase_manager import WorkflowPhaseManager
    from autobyteus.workflow.context.team_manager import TeamManager
    from autobyteus.workflow.streaming.agent_event_multiplexer import AgentEventMultiplexer
    from autobyteus.agent.context import AgentConfig
    from autobyteus.workflow.context.workflow_node_config import WorkflowNodeConfig

logger = logging.getLogger(__name__)

class WorkflowContext:
    """Represents the complete operational context for a single workflow instance."""
    def __init__(self, workflow_id: str, config: 'WorkflowConfig', state: 'WorkflowRuntimeState'):
        if not workflow_id or not isinstance(workflow_id, str):
            raise ValueError("WorkflowContext requires a non-empty string 'workflow_id'.")
        
        self.workflow_id: str = workflow_id
        self.config: 'WorkflowConfig' = config
        self.state: 'WorkflowRuntimeState' = state
        self._node_config_map: Optional[Dict[str, 'WorkflowNodeConfig']] = None
        
        logger.info(f"WorkflowContext composed for workflow_id '{self.workflow_id}'.")

    def get_node_config_by_name(self, name: str) -> Optional['WorkflowNodeConfig']:
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
    def phase_manager(self) -> Optional['WorkflowPhaseManager']:
        return self.state.phase_manager_ref

    @property
    def team_manager(self) -> Optional['TeamManager']:
        return self.state.team_manager
        
    @property
    def multiplexer(self) -> Optional['AgentEventMultiplexer']:
        return self.state.multiplexer_ref
