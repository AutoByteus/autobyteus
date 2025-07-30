# file: autobyteus/autobyteus/cli/workflow_tui/widgets/agent_list_sidebar.py
"""
Defines the sidebar widget that lists all agents in the workflow.
"""

import logging
from typing import Dict, Optional

from textual.message import Message
from textual.widgets import Static, Tree
from textual.widgets.tree import TreeNode

from autobyteus.agent.phases import AgentOperationalPhase

logger = logging.getLogger(__name__)

# A mapping from agent operational phases to display icons.
PHASE_ICONS: Dict[AgentOperationalPhase, str] = {
    AgentOperationalPhase.UNINITIALIZED: "⚪",
    AgentOperationalPhase.BOOTSTRAPPING: "⏳",
    AgentOperationalPhase.IDLE: "🟢",
    AgentOperationalPhase.PROCESSING_USER_INPUT: "💭",
    AgentOperationalPhase.AWAITING_LLM_RESPONSE: "💭",
    AgentOperationalPhase.ANALYZING_LLM_RESPONSE: "🤔",
    AgentOperationalPhase.AWAITING_TOOL_APPROVAL: "❓",
    AgentOperationalPhase.TOOL_DENIED: "❌",
    AgentOperationalPhase.EXECUTING_TOOL: "🛠️",
    AgentOperationalPhase.PROCESSING_TOOL_RESULT: "⚙️",
    AgentOperationalPhase.SHUTTING_DOWN: "🌙",
    AgentOperationalPhase.SHUTDOWN_COMPLETE: "⚫",
    AgentOperationalPhase.ERROR: "❗",
}
DEFAULT_ICON = "❓"

class AgentListSidebar(Static):
    """A widget to display the list of agents in the workflow."""

    class AgentSelected(Message):
        """Posted when an agent is selected in the tree."""
        def __init__(self, agent_name: str) -> None:
            self.agent_name = agent_name
            super().__init__()

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._agent_nodes: Dict[str, TreeNode] = {}
        self.speaking_timers: Dict[str, Optional[object]] = {}


    def compose(self):
        """Compose the widget's contents."""
        yield Tree("Agents", id="agent-tree")

    def on_mount(self) -> None:
        """Called when the widget is mounted."""
        self.query_one(Tree).show_root = False

    def on_tree_node_selected(self, event: Tree.NodeSelected) -> None:
        """Handle agent selection from the tree."""
        agent_name = event.node.data
        if agent_name:
            logger.info(f"Sidebar: User selected agent '{agent_name}'. Posting AgentSelected message.")
            self.post_message(self.AgentSelected(agent_name))

    def add_agent(self, agent_name: str, is_coordinator: bool = False) -> None:
        """Adds a new agent to the list."""
        if agent_name in self._agent_nodes:
            logger.warning(f"Attempted to add agent '{agent_name}' that already exists in the sidebar.")
            return

        tree = self.query_one(Tree)
        # Store the node data as the agent name for easy retrieval.
        node = tree.root.add(agent_name, data=agent_name)
        self._agent_nodes[agent_name] = node
        logger.info(f"Added agent '{agent_name}' to the sidebar.")

        # If it's the first agent (coordinator), select it by default.
        if is_coordinator:
            tree.select_node(node)
            tree.scroll_to_node(node, animate=False)

    def _get_status_label(self, agent_name: str, phase: AgentOperationalPhase) -> str:
        """Constructs the label with icon and name."""
        icon = PHASE_ICONS.get(phase, DEFAULT_ICON)
        return f"{icon} {agent_name}"

    def update_agent_status(self, agent_name: str, phase: AgentOperationalPhase) -> None:
        """Updates the status icon for a given agent."""
        if agent_name not in self._agent_nodes:
            logger.warning(f"Cannot update status for unknown agent '{agent_name}'.")
            return
        
        # Stop any temporary "speaking" timer for this agent
        if agent_name in self.speaking_timers and self.speaking_timers[agent_name] is not None:
            self.speaking_timers[agent_name].stop()
            self.speaking_timers[agent_name] = None
        
        node = self._agent_nodes[agent_name]
        node.set_label(self._get_status_label(agent_name, phase))
        logger.debug(f"Updated agent '{agent_name}' status in sidebar to '{phase.value}'.")
    
    def update_agent_activity_to_speaking(self, agent_name: str, base_phase: AgentOperationalPhase) -> None:
        """Temporarily sets an agent's status to 'Speaking'."""
        if agent_name not in self._agent_nodes:
            return
            
        node = self._agent_nodes[agent_name]
        node.set_label(f"🔊 {agent_name}")

        # If there's an existing timer, cancel it
        if agent_name in self.speaking_timers and self.speaking_timers[agent_name] is not None:
            self.speaking_timers[agent_name].stop()

        # Set a timer to revert to the base phase status after a short delay
        self.speaking_timers[agent_name] = self.set_timer(2.0, lambda: self.update_agent_status(agent_name, base_phase))
