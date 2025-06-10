# file: autobyteus/autobyteus/agent/group/agent_group_context.py
import logging
from typing import List, Dict, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from autobyteus.agent.agent import Agent 

logger = logging.getLogger(__name__)

class AgentGroupContext:
    """
    Stores contextual information about an agent group, including its ID,
    member agents, and the designated coordinator. Provides methods to
    discover agents within the group.
    """
    def __init__(self,
                 group_id: str,
                 agents: List['Agent'],
                 coordinator_agent_id: str):
        """
        Initializes the AgentGroupContext.
        """
        if not group_id or not isinstance(group_id, str):
            raise ValueError("AgentGroupContext requires a non-empty string 'group_id'.")
        if not coordinator_agent_id or not isinstance(coordinator_agent_id, str):
            raise ValueError("AgentGroupContext requires a non-empty string 'coordinator_agent_id'.")
        if not agents:
            raise ValueError("AgentGroupContext requires a non-empty list of 'agents'.")

        from autobyteus.agent.agent import Agent as AgentClassRef
        if not all(isinstance(agent, AgentClassRef) for agent in agents):
            raise TypeError("All items in 'agents' list must be instances of the 'Agent' class.")

        self.group_id: str = group_id
        self._agents_by_id: Dict[str, 'Agent'] = {agent.agent_id: agent for agent in agents}
        self._coordinator_agent_id: str = coordinator_agent_id

        if self._coordinator_agent_id not in self._agents_by_id:
            logger.error(f"Coordinator agent with ID '{self._coordinator_agent_id}' not found in the provided list of agents for group '{self.group_id}'.")
        
        logger.info(f"AgentGroupContext initialized for group_id '{self.group_id}'.")

    def get_agent(self, agent_id: str) -> Optional['Agent']:
        """
        Retrieves an agent from the group by its unique agent_id.
        """
        return self._agents_by_id.get(agent_id)

    def get_agents_by_role(self, role_name: str) -> List['Agent']:
        """
        Retrieves all agents within the group that match the specified role name.
        """
        if not isinstance(role_name, str):
            logger.warning(f"Attempted to get_agents_by_role with non-string role_name: {role_name} in group '{self.group_id}'.")
            return []
            
        matching_agents: List['Agent'] = [
            agent for agent in self._agents_by_id.values()
            if agent.context and agent.context.config and agent.context.config.role == role_name
        ]
        
        if not matching_agents:
            logger.debug(f"No agents found with role '{role_name}' in group '{self.group_id}'.")
        return matching_agents

    def get_coordinator_agent(self) -> Optional['Agent']:
        """
        Retrieves the designated coordinator agent for this group.
        """
        return self.get_agent(self._coordinator_agent_id)

    def get_all_agents(self) -> List['Agent']:
        """
        Retrieves all agents currently part of this group.
        """
        return list(self._agents_by_id.values())

    def __repr__(self) -> str:
        return (f"<AgentGroupContext group_id='{self.group_id}', "
                f"num_agents={len(self._agents_by_id)}, "
                f"coordinator_id='{self._coordinator_agent_id}'>")
