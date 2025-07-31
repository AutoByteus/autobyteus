# file: autobyteus/autobyteus/cli/workflow_tui/widgets/agent_list_sidebar.py
"""
Defines the sidebar widget that lists all nodes in the workflow hierarchy.
"""
import logging
from typing import Dict, Any, Optional

from textual.message import Message
from textual.widgets import Static, Tree
from textual.widgets.tree import TreeNode

from autobyteus.agent.phases import AgentOperationalPhase
from autobyteus.workflow.phases import WorkflowOperationalPhase
from .shared import (
    AGENT_PHASE_ICONS, WORKFLOW_PHASE_ICONS, SUB_WORKFLOW_ICON, 
    WORKFLOW_ICON, SPEAKING_ICON, DEFAULT_ICON
)

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
        yield Tree("Workflow", id="agent-tree")

    def on_tree_node_selected(self, event: Tree.NodeSelected) -> None:
        """Handle node selection from the tree."""
        if event.node.data:
            self.post_message(self.NodeSelected(event.node.data))
        event.stop()

    def update_tree(self, tree_data: Dict, agent_phases: Dict[str, AgentOperationalPhase], workflow_phases: Dict[str, WorkflowOperationalPhase], speaking_agents: Dict[str, bool]):
        """Rebuilds the entire tree from the state store data."""
        tree = self.query_one(Tree)
        tree.clear()
        self._node_map.clear()

        if not tree_data:
            tree.root.set_label("Initializing workflow...")
            return

        root_name = list(tree_data.keys())[0]
        root_node_data = tree_data[root_name]
        
        root_phase = workflow_phases.get(root_name, WorkflowOperationalPhase.UNINITIALIZED)
        root_icon = WORKFLOW_PHASE_ICONS.get(root_phase, WORKFLOW_ICON)
        
        root_label = f"{root_icon} {root_node_data.get('role') or root_name}"
        if root_node_data.get('role') and root_node_data.get('role') != root_name:
            root_label += f" ({root_name})"
        
        tree.root.set_label(root_label)
        tree.root.data = root_node_data
        self._node_map[root_name] = tree.root
        
        self._build_tree_recursively(tree.root, root_node_data.get("children", {}), agent_phases, workflow_phases, speaking_agents)
        tree.show_root = True
        tree.root.expand()

    def _build_tree_recursively(self, parent_node: TreeNode, children_data: Dict, agent_phases: Dict, workflow_phases: Dict, speaking_agents: Dict):
        """Helper to recursively build the tree."""
        for name, node_data in children_data.items():
            node_type = node_data["type"]
            
            if node_type == "agent":
                phase = agent_phases.get(name, AgentOperationalPhase.UNINITIALIZED)
                icon = SPEAKING_ICON if speaking_agents.get(name) else AGENT_PHASE_ICONS.get(phase, DEFAULT_ICON)
                label = f"{icon} {name}"
                new_node = parent_node.add_leaf(label, data=node_data)
            elif node_type == "subworkflow":
                phase = workflow_phases.get(name, WorkflowOperationalPhase.UNINITIALIZED)
                icon = WORKFLOW_PHASE_ICONS.get(phase, SUB_WORKFLOW_ICON)
                role = node_data.get("role")
                label = f"{icon} {role or name}"
                if role and role != name:
                    label += f" ({name})"
                new_node = parent_node.add(label, data=node_data)
                self._build_tree_recursively(new_node, node_data.get("children", {}), agent_phases, workflow_phases, speaking_agents)
            
            self._node_map[name] = new_node

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
