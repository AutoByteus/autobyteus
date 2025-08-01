# file: autobyteus/autobyteus/workflow/context/workflow_node_config.py
from __future__ import annotations
import logging
import uuid
from dataclasses import dataclass, field
from typing import List, TYPE_CHECKING, Union, Tuple

# The import is moved into the TYPE_CHECKING block to break the circular dependency at module load time.
if TYPE_CHECKING:
    from autobyteus.agent.context import AgentConfig
    from autobyteus.workflow.context.workflow_config import WorkflowConfig

logger = logging.getLogger(__name__)

@dataclass
class WorkflowNodeConfig:
    """
    Represents a node in an agentic workflow graph.

    This is the core building block for defining workflows. A node can be either
    a single agent (defined by an AgentConfig) or an entire sub-workflow
    (defined by a WorkflowConfig).

    Attributes:
        node_definition: The configuration for the agent or sub-workflow at this node.
        dependencies: A tuple of other WorkflowNodeConfig objects that must be
                      successfully executed before this node can be executed.
        node_id: A unique identifier for this node instance.
    """
    node_definition: Union["AgentConfig", "WorkflowConfig"]
    dependencies: Tuple[WorkflowNodeConfig, ...] = field(default_factory=tuple)
    node_id: str = field(default_factory=lambda: f"node_{uuid.uuid4().hex}", init=False, repr=False)

    def __post_init__(self):
        """Validates the node configuration."""
        from autobyteus.agent.context import AgentConfig
        from autobyteus.workflow.context.workflow_config import WorkflowConfig
        
        if not isinstance(self.node_definition, (AgentConfig, WorkflowConfig)):
            raise TypeError("The 'node_definition' attribute must be an instance of AgentConfig or WorkflowConfig.")
        
        if not all(isinstance(dep, WorkflowNodeConfig) for dep in self.dependencies):
            raise TypeError("All items in 'dependencies' must be instances of WorkflowNodeConfig.")

        logger.debug(f"WorkflowNodeConfig created for: '{self.name}' (NodeID: {self.node_id}). Dependencies: {[dep.name for dep in self.dependencies]}")

    @property
    def name(self) -> str:
        """A convenience property to get the node's name from its definition."""
        return self.node_definition.name

    @property
    def effective_config(self) -> Union["AgentConfig", "WorkflowConfig"]:
        """Returns the underlying AgentConfig or WorkflowConfig."""
        return self.node_definition

    @property
    def is_subworkflow(self) -> bool:
        """Returns True if this node represents a sub-workflow."""
        from autobyteus.workflow.context.workflow_config import WorkflowConfig
        return isinstance(self.node_definition, WorkflowConfig)
    
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
