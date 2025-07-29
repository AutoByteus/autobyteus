# file: autobyteus/autobyteus/agent/workflow/context/workflow_node_config.py
from __future__ import annotations
import logging
import uuid
from dataclasses import dataclass, field
from typing import List, TYPE_CHECKING

# The import is moved into the TYPE_CHECKING block to break the circular dependency at module load time.
if TYPE_CHECKING:
    from autobyteus.agent.context import AgentConfig

logger = logging.getLogger(__name__)

@dataclass
class WorkflowNodeConfig:
    """
    Represents a node in an agentic workflow graph.

    This is the core building block for defining workflows. A node is defined
    by an AgentConfig, which the framework uses to instantiate the agent lazily.
    Each node instance is unique, identified by an internal `node_id`.

    Attributes:
        agent_config: The configuration for an agent.
        dependencies: A list of other WorkflowNodeConfig objects that must be
                      successfully executed before this node can be executed.
        node_id: A unique identifier for this node instance.
    """
    agent_config: "AgentConfig"
    dependencies: List[WorkflowNodeConfig] = field(default_factory=list)
    node_id: str = field(default_factory=lambda: f"node_{uuid.uuid4().hex}", init=False, repr=False)

    def __post_init__(self):
        """Validates the node configuration."""
        # A local import is used here for the runtime type check,
        # ensuring the class is available when an object is created.
        from autobyteus.agent.context import AgentConfig
        
        if not isinstance(self.agent_config, AgentConfig):
            raise TypeError("The 'agent_config' attribute must be an instance of AgentConfig.")
        
        if not all(isinstance(dep, WorkflowNodeConfig) for dep in self.dependencies):
            raise TypeError("All items in 'dependencies' must be instances of WorkflowNodeConfig.")

        logger.debug(f"WorkflowNodeConfig created for agent: '{self.name}' (NodeID: {self.node_id}). Dependencies: {[dep.name for dep in self.dependencies]}")

    @property
    def name(self) -> str:
        """A convenience property to get the agent's name."""
        return self.agent_config.name

    @property
    def effective_config(self) -> "AgentConfig":
        """Returns the AgentConfig."""
        return self.agent_config
    
    def __hash__(self):
        """
        Makes the node hashable based on its unique node_id, allowing it to be
        used in sets and as dictionary keys.
        """
        return hash(self.node_id)
    
    def __eq__(self, other):
        """
        Compares two nodes based on their unique node_id.
        """
        if isinstance(other, WorkflowNodeConfig):
            return self.node_id == other.node_id
        return False
