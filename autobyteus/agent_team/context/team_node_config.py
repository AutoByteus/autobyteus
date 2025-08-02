# file: autobyteus/autobyteus/agent_team/context/team_node_config.py
from __future__ import annotations
import logging
import uuid
from dataclasses import dataclass, field
from typing import List, TYPE_CHECKING, Union, Tuple

# The import is moved into the TYPE_CHECKING block to break the circular dependency at module load time.
if TYPE_CHECKING:
    from autobyteus.agent.context import AgentConfig
    from autobyteus.agent_team.context.agent_team_config import AgentTeamConfig

logger = logging.getLogger(__name__)

@dataclass
class TeamNodeConfig:
    """
    Represents a node in an agent team graph.

    This is the core building block for defining agent teams. A node can be either
    a single agent (defined by an AgentConfig) or an entire sub-team
    (defined by an AgentTeamConfig).

    Attributes:
        node_definition: The configuration for the agent or sub-team at this node.
        dependencies: A tuple of other TeamNodeConfig objects that must be
                      successfully executed before this node can be executed.
        node_id: A unique identifier for this node instance.
    """
    node_definition: Union["AgentConfig", "AgentTeamConfig"]
    dependencies: Tuple[TeamNodeConfig, ...] = field(default_factory=tuple)
    node_id: str = field(default_factory=lambda: f"node_{uuid.uuid4().hex}", init=False, repr=False)

    def __post_init__(self):
        """Validates the node configuration."""
        from autobyteus.agent.context import AgentConfig
        from autobyteus.agent_team.context.agent_team_config import AgentTeamConfig
        
        if not isinstance(self.node_definition, (AgentConfig, AgentTeamConfig)):
            raise TypeError("The 'node_definition' attribute must be an instance of AgentConfig or AgentTeamConfig.")
        
        if not all(isinstance(dep, TeamNodeConfig) for dep in self.dependencies):
            raise TypeError("All items in 'dependencies' must be instances of TeamNodeConfig.")

        logger.debug(f"TeamNodeConfig created for: '{self.name}' (NodeID: {self.node_id}). Dependencies: {[dep.name for dep in self.dependencies]}")

    @property
    def name(self) -> str:
        """A convenience property to get the node's name from its definition."""
        return self.node_definition.name

    @property
    def effective_config(self) -> Union["AgentConfig", "AgentTeamConfig"]:
        """Returns the underlying AgentConfig or AgentTeamConfig."""
        return self.node_definition

    @property
    def is_sub_team(self) -> bool:
        """Returns True if this node represents a sub-team."""
        from autobyteus.agent_team.context.agent_team_config import AgentTeamConfig
        return isinstance(self.node_definition, AgentTeamConfig)
    
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
        if isinstance(other, TeamNodeConfig):
            return self.node_id == other.node_id
        return False
