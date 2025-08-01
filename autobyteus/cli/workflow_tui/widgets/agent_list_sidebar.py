# file: autobyteus/autobyteus/cli/workflow_tui/widgets/agent_list_sidebar.py
"""
Defines the sidebar widget that lists all nodes in the workflow hierarchy.
"""
import logging
from typing import Dict, Any, Optional

from textual.message import Message
from textual.widgets import Static, Tree
from textual.widgets.tree import TreeNode
from textual.containers import Vertical

from autobyteus.agent.phases import AgentOperationalPhase
from autobyteus.workflow.phases import WorkflowOperationalPhase
from .shared import (
    AGENT_PHASE_ICONS, WORKFLOW_PHASE_ICONS, SUB_WORKFLOW_ICON, 
    WORKFLOW_ICON, SPEAKING_ICON, DEFAULT_ICON
)
from .logo import Logo

logger = logging.getLogger(__name__)

class AgentListSidebar(Static):
    """A widget to display the hierarchical list of workflow nodes. This is a dumb
    rendering component driven by the TUIStateStore."""

    class NodeSelected(Message):
        """Posted when any node is selected in the tree."""
        def __init__(self, node_data: Dict[str, Any]) -> None:
            self.node_data = node_data
            super().__init__()

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._node_map: Dict[str, TreeNode] = {} # Maps node names to TreeNode objects

    def compose(self):
        with Vertical():
            yield Tree("Workflow", id="agent-tree")
            yield Logo()

    def on_tree_node_selected(self, event: Tree.NodeSelected) -> None:
        """Handle node selection from the tree."""
        if event.node.data:
            self.post_message(self.NodeSelected(event.node.data))
        event.stop()

    def _build_label(self, name: str, node_data: Dict, agent_phases: Dict, workflow_phases: Dict, speaking_agents: Dict) -> str:
        """Constructs the display label for a tree node."""
        node_type = node_data["type"]
        icon = DEFAULT_ICON
        
        if node_type == "agent":
            phase = agent_phases.get(name, AgentOperationalPhase.UNINITIALIZED)
            icon = SPEAKING_ICON if speaking_agents.get(name) else AGENT_PHASE_ICONS.get(phase, DEFAULT_ICON)
            label = f"{icon} {name}"
        elif node_type in ["workflow", "subworkflow"]:
            phase = workflow_phases.get(name, WorkflowOperationalPhase.UNINITIALIZED)
            default_icon = WORKFLOW_ICON if node_type == "workflow" else SUB_WORKFLOW_ICON
            icon = WORKFLOW_PHASE_ICONS.get(phase, default_icon)
            role = node_data.get("role")
            label = f"{icon} {role or name}"
            if role and role != name:
                label += f" ({name})"
        else:
            label = f"{icon} {name}"
            
        return label

    def update_tree(self, tree_data: Dict, agent_phases: Dict[str, AgentOperationalPhase], workflow_phases: Dict[str, WorkflowOperationalPhase], speaking_agents: Dict[str, bool]):
        """
        Performs an in-place update of the tree to reflect the new state,
        avoiding a full rebuild for better performance and preserving UI state like expansion.
        """
        tree = self.query_one(Tree)

        if not tree_data:
            tree.root.set_label("Initializing workflow...")
            return

        root_name = list(tree_data.keys())[0]
        root_node_data = tree_data[root_name]

        # Kick off the recursive update from the root.
        self._update_node_recursively(tree.root, root_node_data, agent_phases, workflow_phases, speaking_agents)
        
        # Ensure the root is expanded on the first run.
        if not tree.root.is_expanded:
            tree.root.expand()

    def _update_node_recursively(self, ui_node: TreeNode, node_data: Dict, agent_phases: Dict, workflow_phases: Dict, speaking_agents: Dict):
        """Recursively updates a node and reconciles its children."""
        # 1. Update the current node's label and data
        name = node_data['name']
        label = self._build_label(name, node_data, agent_phases, workflow_phases, speaking_agents)
        ui_node.set_label(label)
        ui_node.data = node_data
        self._node_map[name] = ui_node  # Ensure map is always up-to-date

        # 2. Reconcile children
        new_children_data = node_data.get("children", {})
        existing_ui_children_by_name = {child.data['name']: child for child in ui_node.children if child.data}

        # Add new nodes and update existing ones
        for child_name, child_data in new_children_data.items():
            if child_name in existing_ui_children_by_name:
                # Node exists, so we recursively update it
                child_ui_node = existing_ui_children_by_name[child_name]
                self._update_node_recursively(child_ui_node, child_data, agent_phases, workflow_phases, speaking_agents)
            else:
                # Node is new, so we add it
                new_child_label = self._build_label(child_name, child_data, agent_phases, workflow_phases, speaking_agents)
                is_leaf = child_data.get("children", {}) == {} and child_data['type'] == 'agent'
                
                if is_leaf:
                    new_ui_node = ui_node.add_leaf(new_child_label, data=child_data)
                else:
                    new_ui_node = ui_node.add(new_child_label, data=child_data)
                    # Since this is a new branch, we must build its children too
                    self._update_node_recursively(new_ui_node, child_data, agent_phases, workflow_phases, speaking_agents)
                
                self._node_map[child_name] = new_ui_node

        # Remove old nodes that no longer exist in the new data
        nodes_to_remove = []
        for existing_child_name, existing_child_node in existing_ui_children_by_name.items():
            if existing_child_name not in new_children_data:
                nodes_to_remove.append(existing_child_node)
                if existing_child_name in self._node_map:
                    del self._node_map[existing_child_name]
        
        for node in nodes_to_remove:
            node.remove()

    def update_selection(self, node_name: Optional[str]):
        """Updates the tree's selection and expands parents to make it visible."""
        if not node_name or node_name not in self._node_map:
            return
            
        tree = self.query_one(Tree)
        node_to_select = self._node_map[node_name]
        
        parent = node_to_select.parent
        while parent:
            parent.expand()
            parent = parent.parent
        
        tree.select_node(node_to_select)
        tree.scroll_to_node(node_to_select)
