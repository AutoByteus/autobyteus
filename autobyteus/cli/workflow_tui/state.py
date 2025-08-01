# file: autobyteus/autobyteus/cli/workflow_tui/state.py
"""
Defines a centralized state store for the TUI application, following state management best practices.
"""
import logging
from typing import Dict, List, Optional, Any
import copy

from autobyteus.agent.context import AgentConfig
from autobyteus.workflow.agentic_workflow import AgenticWorkflow
from autobyteus.agent.phases import AgentOperationalPhase
from autobyteus.workflow.phases import WorkflowOperationalPhase
from autobyteus.agent.streaming.stream_events import StreamEvent as AgentStreamEvent, StreamEventType as AgentStreamEventType
from autobyteus.agent.streaming.stream_event_payloads import (
    AgentOperationalPhaseTransitionData, ToolInvocationApprovalRequestedData, 
    AssistantChunkData, AssistantCompleteResponseData
)
from autobyteus.workflow.streaming.workflow_stream_events import WorkflowStreamEvent
from autobyteus.workflow.streaming.workflow_stream_event_payloads import AgentEventRebroadcastPayload, SubWorkflowEventRebroadcastPayload, WorkflowPhaseTransitionData

logger = logging.getLogger(__name__)

class TUIStateStore:
    """
    A centralized store for all TUI-related state.

    This class acts as the single source of truth for the UI. It processes events
    from the backend and updates its state. The main App class can then react to
    these state changes to update the UI components declaratively. This is a plain
    Python class and does not use Textual reactive properties.
    """

    def __init__(self, workflow: AgenticWorkflow):
        self.workflow_name = workflow.name
        self.workflow_role = workflow.role
        
        self.focused_node_data: Optional[Dict[str, Any]] = None
        
        self._node_roles: Dict[str, str] = self._extract_node_roles(workflow)
        self._nodes: Dict[str, Any] = self._initialize_root_node()
        self._agent_phases: Dict[str, AgentOperationalPhase] = {}
        self._workflow_phases: Dict[str, WorkflowOperationalPhase] = {self.workflow_name: WorkflowOperationalPhase.UNINITIALIZED}
        self._agent_event_history: Dict[str, List[AgentStreamEvent]] = {}
        self._workflow_event_history: Dict[str, List[WorkflowStreamEvent]] = {self.workflow_name: []}
        self._pending_approvals: Dict[str, ToolInvocationApprovalRequestedData] = {}
        self._speaking_agents: Dict[str, bool] = {}
        
        # REMOVED: The complex stream aggregator is the source of the bug.
        # self._agent_stream_aggregators: Dict[str, Dict[str, str]] = {}

        # Version counter to signal state changes to the UI
        self.version = 0

    def _extract_node_roles(self, workflow: AgenticWorkflow) -> Dict[str, str]:
        """Builds a map of node names to their defined roles from the config."""
        roles = {}
        if workflow._runtime and workflow._runtime.context and workflow._runtime.context.config:
            for node_config in workflow._runtime.context.config.nodes:
                role = getattr(node_config.node_definition, 'role', None)
                if role:
                    roles[node_config.name] = role
        return roles

    def _initialize_root_node(self) -> Dict[str, Any]:
        """Creates the initial root node for the state tree."""
        return {
            self.workflow_name: {
                "type": "workflow",
                "name": self.workflow_name,
                "role": self.workflow_role,
                "children": {}
            }
        }

    def process_event(self, event: WorkflowStreamEvent):
        """
        The main entry point for processing events from the backend.
        This method acts as a reducer, updating the state based on the event.
        """
        if event.event_source_type == "WORKFLOW" and isinstance(event.data, WorkflowPhaseTransitionData):
            self._workflow_phases[self.workflow_name] = event.data.new_phase
        
        self._process_event_recursively(event, self.workflow_name)
        
        # Increment version to signal that the state has changed.
        self.version += 1

    # REMOVED: The flush aggregator logic is no longer needed.
    # def _flush_aggregator_for_agent(self, agent_name: str): ...

    def _process_event_recursively(self, event: WorkflowStreamEvent, parent_name: str):
        """Recursively processes events to build up the state tree."""
        if parent_name not in self._workflow_event_history:
            self._workflow_event_history[parent_name] = []
        self._workflow_event_history[parent_name].append(event)

        # AGENT EVENT (LEAF NODE)
        if isinstance(event.data, AgentEventRebroadcastPayload):
            payload = event.data
            agent_name = payload.agent_name
            agent_event = payload.agent_event

            if agent_name not in self._agent_event_history:
                self._agent_event_history[agent_name] = []
                if self._find_node(parent_name):
                    agent_role = self._node_roles.get(agent_name, "Agent")
                    self._add_node(agent_name, {"type": "agent", "name": agent_name, "role": agent_role, "children": {}}, parent_name)
                else:
                    logger.error(f"Cannot add agent node '{agent_name}': parent '{parent_name}' not found in state tree.")

            # SIMPLIFIED LOGIC: Always append the event to the history, regardless of focus.
            # This ensures the history is always a complete and accurate log of what happened.
            self._agent_event_history[agent_name].append(agent_event)

            # --- State update logic for specific events (applies to both focused and non-focused) ---
            if agent_event.event_type == AgentStreamEventType.AGENT_OPERATIONAL_PHASE_TRANSITION:
                phase_data: AgentOperationalPhaseTransitionData = agent_event.data
                self._agent_phases[agent_name] = phase_data.new_phase
                if agent_name in self._pending_approvals:
                    del self._pending_approvals[agent_name]
            elif agent_event.event_type == AgentStreamEventType.AGENT_IDLE:
                self._agent_phases[agent_name] = AgentOperationalPhase.IDLE
            elif agent_event.event_type == AgentStreamEventType.TOOL_INVOCATION_APPROVAL_REQUESTED:
                self._pending_approvals[agent_name] = agent_event.data

        # SUB-WORKFLOW EVENT (BRANCH NODE)
        elif isinstance(event.data, SubWorkflowEventRebroadcastPayload):
            payload = event.data
            sub_workflow_name = payload.sub_workflow_node_name
            sub_workflow_event = payload.sub_workflow_event
            
            sub_workflow_node = self._find_node(sub_workflow_name)
            if not sub_workflow_node:
                role = self._node_roles.get(sub_workflow_name, "Sub-Workflow")
                self._add_node(sub_workflow_name, {"type": "subworkflow", "name": sub_workflow_name, "role": role, "children": {}}, parent_name)

            if sub_workflow_event.event_source_type == "WORKFLOW" and isinstance(sub_workflow_event.data, WorkflowPhaseTransitionData):
                self._workflow_phases[sub_workflow_name] = sub_workflow_event.data.new_phase

            self._process_event_recursively(sub_workflow_event, parent_name=sub_workflow_name)

    def _add_node(self, node_name: str, node_data: Dict, parent_name: str):
        """Adds a node to the state tree under a specific parent."""
        parent = self._find_node(parent_name)
        if parent:
            parent["children"][node_name] = node_data
        else:
            logger.error(f"Could not find parent node '{parent_name}' to add child '{node_name}'.")

    def _find_node(self, node_name: str, tree: Optional[Dict] = None) -> Optional[Dict]:
        """Recursively finds a node by name in the state tree."""
        if tree is None:
            tree = self._nodes
        
        for name, node_data in tree.items():
            if name == node_name:
                return node_data
            if node_data.get("children"):
                found = self._find_node(node_name, node_data.get("children"))
                if found:
                    return found
        return None

    def get_tree_data(self) -> Dict:
        """Constructs a serializable representation of the tree for the sidebar."""
        return copy.deepcopy(self._nodes)
    
    def get_history_for_node(self, node_name: str, node_type: str) -> List:
        """Retrieves the event history for a given node."""
        if node_type == 'agent':
            # REMOVED: Flushing is no longer necessary as the history is always complete.
            return self._agent_event_history.get(node_name, [])
        elif node_type in ['workflow', 'subworkflow']:
            return []
        return []
        
    def get_pending_approval_for_agent(self, agent_name: str) -> Optional[ToolInvocationApprovalRequestedData]:
        """Gets pending approval data for a specific agent."""
        return self._pending_approvals.get(agent_name)

    def clear_pending_approval(self, agent_name: str):
        """Clears a pending approval after it's been handled."""
        if agent_name in self._pending_approvals:
            del self._pending_approvals[agent_name]
    
    def set_focused_node(self, node_data: Optional[Dict[str, Any]]):
        """Sets the currently focused node in the state."""
        # REMOVED: Flushing logic is no longer needed here.
        self.focused_node_data = node_data
