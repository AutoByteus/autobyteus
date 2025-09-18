"""
Defines a centralized state store for the TUI application, following state management best practices.
"""
import logging
from typing import Dict, List, Optional, Any
import copy

from autobyteus.agent.context import AgentConfig
from autobyteus.agent_team.agent_team import AgentTeam
from autobyteus.agent.phases import AgentOperationalPhase
from autobyteus.agent_team.phases import AgentTeamOperationalPhase
from autobyteus.agent.streaming.stream_events import StreamEvent as AgentStreamEvent, StreamEventType as AgentStreamEventType
from autobyteus.agent.streaming.stream_event_payloads import (
    AgentOperationalPhaseTransitionData, ToolInvocationApprovalRequestedData, 
    AssistantChunkData, AssistantCompleteResponseData
)
from autobyteus.agent_team.streaming.agent_team_stream_events import AgentTeamStreamEvent
from autobyteus.agent_team.streaming.agent_team_stream_event_payloads import AgentEventRebroadcastPayload, SubTeamEventRebroadcastPayload, AgentTeamPhaseTransitionData
from autobyteus.task_management.task import Task
from autobyteus.task_management.events import TasksAddedEvent, TaskStatusUpdatedEvent
from autobyteus.task_management.base_task_board import TaskStatus

logger = logging.getLogger(__name__)

class TUIStateStore:
    """
    A centralized store for all TUI-related state.

    This class acts as the single source of truth for the UI. It processes events
    from the backend and updates its state. The main App class can then react to
    these state changes to update the UI components declaratively.
    """

    def __init__(self, team: AgentTeam):
        self.team_name = team.name
        self.team_role = team.role
        
        self.focused_node_data: Optional[Dict[str, Any]] = None
        
        self._node_roles: Dict[str, str] = self._extract_node_roles(team)
        self._nodes: Dict[str, Any] = self._initialize_root_node()
        self._agent_phases: Dict[str, AgentOperationalPhase] = {}
        self._team_phases: Dict[str, AgentTeamOperationalPhase] = {self.team_name: AgentTeamOperationalPhase.UNINITIALIZED}
        self._agent_event_history: Dict[str, List[AgentStreamEvent]] = {}
        self._team_event_history: Dict[str, List[AgentTeamStreamEvent]] = {self.team_name: []}
        self._pending_approvals: Dict[str, ToolInvocationApprovalRequestedData] = {}
        self._speaking_agents: Dict[str, bool] = {}
        
        # State for task boards
        self._task_plans: Dict[str, List[Task]] = {} # team_name -> List[Task]
        self._task_statuses: Dict[str, Dict[str, TaskStatus]] = {} # team_name -> {task_id: status}
        
        # Version counter to signal state changes to the UI
        self.version = 0

    def _extract_node_roles(self, team: AgentTeam) -> Dict[str, str]:
        roles = {}
        if team._runtime and team._runtime.context and team._runtime.context.config:
            for node_config in team._runtime.context.config.nodes:
                role = getattr(node_config.node_definition, 'role', None)
                if role:
                    roles[node_config.name] = role
        return roles

    def _initialize_root_node(self) -> Dict[str, Any]:
        return {
            self.team_name: {
                "type": "team",
                "name": self.team_name,
                "role": self.team_role,
                "children": {}
            }
        }

    def process_event(self, event: AgentTeamStreamEvent):
        self.version += 1 # Increment on any event to signal a change
        
        if event.event_source_type == "TEAM" and isinstance(event.data, AgentTeamPhaseTransitionData):
            self._team_phases[self.team_name] = event.data.new_phase
        
        self._process_event_recursively(event, self.team_name)

    def _process_event_recursively(self, event: AgentTeamStreamEvent, parent_name: str):
        if parent_name not in self._team_event_history:
            self._team_event_history[parent_name] = []
        self._team_event_history[parent_name].append(event)
        
        if event.event_source_type == "TASK_BOARD":
            team_name_key = parent_name
            if isinstance(event.data, TasksAddedEvent):
                if team_name_key not in self._task_plans: self._task_plans[team_name_key] = []
                if team_name_key not in self._task_statuses: self._task_statuses[team_name_key] = {}
                self._task_plans[team_name_key].extend(event.data.tasks)
                for task in event.data.tasks:
                    self._task_statuses[team_name_key][task.task_id] = TaskStatus.NOT_STARTED
                logger.debug(f"TUI State: Added {len(event.data.tasks)} tasks to board for '{team_name_key}'.")

            elif isinstance(event.data, TaskStatusUpdatedEvent):
                if team_name_key not in self._task_statuses: self._task_statuses[team_name_key] = {}
                self._task_statuses[team_name_key][event.data.task_id] = event.data.new_status
                logger.debug(f"TUI State: Updated status for task '{event.data.task_id}' in team '{team_name_key}' to {event.data.new_status}.")
                
                if event.data.deliverables is not None and team_name_key in self._task_plans:
                    for task in self._task_plans[team_name_key]:
                        if task.task_id == event.data.task_id:
                            task.file_deliverables = event.data.deliverables
                            logger.debug(f"TUI State: Synced deliverables for task '{event.data.task_id}' in team '{team_name_key}'.")
                            break
            return

        if isinstance(event.data, AgentEventRebroadcastPayload):
            payload = event.data
            agent_name = payload.agent_name
            agent_event = payload.agent_event

            if agent_name not in self._agent_event_history:
                self._agent_event_history[agent_name] = []
                if self._find_node(parent_name):
                    agent_role = self._node_roles.get(agent_name, "Agent")
                    self._add_node(agent_name, {"type": "agent", "name": agent_name, "role": agent_role, "children": {}}, parent_name)
                else: logger.error(f"Cannot add agent node '{agent_name}': parent '{parent_name}' not found.")
            self._agent_event_history[agent_name].append(agent_event)

            if agent_event.event_type == AgentStreamEventType.AGENT_OPERATIONAL_PHASE_TRANSITION:
                self._agent_phases[agent_name] = agent_event.data.new_phase
                if agent_name in self._pending_approvals: del self._pending_approvals[agent_name]
            elif agent_event.event_type == AgentStreamEventType.AGENT_IDLE:
                self._agent_phases[agent_name] = AgentOperationalPhase.IDLE
            elif agent_event.event_type == AgentStreamEventType.TOOL_INVOCATION_APPROVAL_REQUESTED:
                self._pending_approvals[agent_name] = agent_event.data

        elif isinstance(event.data, SubTeamEventRebroadcastPayload):
            payload = event.data
            sub_team_name = payload.sub_team_node_name
            sub_team_event = payload.sub_team_event
            if not self._find_node(sub_team_name):
                role = self._node_roles.get(sub_team_name, "Sub-Team")
                self._add_node(sub_team_name, {"type": "subteam", "name": sub_team_name, "role": role, "children": {}}, parent_name)
            if sub_team_event.event_source_type == "TEAM" and isinstance(sub_team_event.data, AgentTeamPhaseTransitionData):
                self._team_phases[sub_team_name] = sub_team_event.data.new_phase
            self._process_event_recursively(sub_team_event, parent_name=sub_team_name)

    def _add_node(self, node_name: str, node_data: Dict, parent_name: str):
        parent = self._find_node(parent_name)
        if parent: parent["children"][node_name] = node_data
        else: logger.error(f"Could not find parent node '{parent_name}' to add child '{node_name}'.")

    def _find_node(self, node_name: str, tree: Optional[Dict] = None) -> Optional[Dict]:
        tree = tree or self._nodes
        for name, node_data in tree.items():
            if name == node_name: return node_data
            if node_data.get("children"):
                found = self._find_node(node_name, node_data.get("children"))
                if found: return found
        return None

    def get_tree_data(self) -> Dict:
        return copy.deepcopy(self._nodes)
    
    def get_history_for_node(self, node_name: str, node_type: str) -> List:
        if node_type == 'agent': return self._agent_event_history.get(node_name, [])
        return []
        
    def get_pending_approval_for_agent(self, agent_name: str) -> Optional[ToolInvocationApprovalRequestedData]:
        return self._pending_approvals.get(agent_name)
        
    def get_task_board_plan(self, team_name: str) -> Optional[List[Task]]:
        return self._task_plans.get(team_name)

    def get_task_board_statuses(self, team_name: str) -> Optional[Dict[str, TaskStatus]]:
        return self._task_statuses.get(team_name)

    def clear_pending_approval(self, agent_name: str):
        if agent_name in self._pending_approvals: del self._pending_approvals[agent_name]
    
    def set_focused_node(self, node_data: Optional[Dict[str, Any]]):
        self.focused_node_data = node_data
