# file: autobyteus/autobyteus/workflow/context/workflow_runtime_state.py
import logging
from typing import List, Optional, TYPE_CHECKING, Dict

from autobyteus.workflow.phases.workflow_operational_phase import WorkflowOperationalPhase
from autobyteus.agent.context import AgentConfig

if TYPE_CHECKING:
    from autobyteus.agent.agent import Agent
    from autobyteus.workflow.events.workflow_input_event_queue_manager import WorkflowInputEventQueueManager
    from autobyteus.workflow.phases.workflow_phase_manager import WorkflowPhaseManager
    from autobyteus.workflow.context.workflow_node_config import WorkflowNodeConfig
    from autobyteus.workflow.context.team_manager import TeamManager

logger = logging.getLogger(__name__)

class WorkflowRuntimeState:
    """Encapsulates the dynamic, stateful data of a running workflow instance."""
    def __init__(self, workflow_id: str):
        if not workflow_id or not isinstance(workflow_id, str):
            raise ValueError("WorkflowRuntimeState requires a non-empty string 'workflow_id'.")

        self.workflow_id: str = workflow_id
        self.current_phase: WorkflowOperationalPhase = WorkflowOperationalPhase.UNINITIALIZED
        
        # State populated by bootstrap steps
        self.prepared_coordinator_prompt: Optional[str] = None
        
        # Core services
        self.team_manager: Optional['TeamManager'] = None

        # Runtime components
        self.input_event_queues: Optional['WorkflowInputEventQueueManager'] = None
        self.phase_manager_ref: Optional['WorkflowPhaseManager'] = None

        logger.info(f"WorkflowRuntimeState initialized for workflow_id '{self.workflow_id}'.")

    def __repr__(self) -> str:
        agents_count = len(self.team_manager.get_all_agents()) if self.team_manager else 0
        coordinator_set = self.team_manager.coordinator_agent is not None if self.team_manager else False
        return (f"<WorkflowRuntimeState id='{self.workflow_id}', phase='{self.current_phase.value}', "
                f"agents_count={agents_count}, coordinator_set={coordinator_set}, "
                f"team_manager_set={self.team_manager is not None}>")
