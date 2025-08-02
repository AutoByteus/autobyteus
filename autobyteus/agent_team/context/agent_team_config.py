# file: autobyteus/autobyteus/agent_team/context/agent_team_config.py
import logging
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

from autobyteus.agent_team.context.team_node_config import TeamNodeConfig

logger = logging.getLogger(__name__)

@dataclass(frozen=True)
class AgentTeamConfig:
    """
    Represents the complete, static configuration for an AgentTeam instance.
    This is the user's primary input for defining an agent team.
    """
    name: str
    description: str
    nodes: Tuple[TeamNodeConfig, ...]
    coordinator_node: TeamNodeConfig
    role: Optional[str] = None

    def __post_init__(self):
        if not self.name or not isinstance(self.name, str):
            raise ValueError("The 'name' in AgentTeamConfig must be a non-empty string.")
        if not self.nodes:
            raise ValueError("The 'nodes' collection in AgentTeamConfig cannot be empty.")
        if self.coordinator_node not in self.nodes:
            raise ValueError("The 'coordinator_node' must be one of the nodes in the 'nodes' collection.")
        logger.debug(f"AgentTeamConfig validated for team: '{self.name}'.")
