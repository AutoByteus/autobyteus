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

        Args:
            group_id: The unique identifier for this agent group.
            agents: A list of all Agent instances belonging to this group.
            coordinator_agent_id: The agent_id of the designated coordinator agent in this group.
        
        Raises:
            ValueError: If group_id or coordinator_agent_id is empty, or if agents list is empty.
            TypeError: If agents list contains non-Agent instances.
        """
        if not group_id or not isinstance(group_id, str):
            raise ValueError("AgentGroupContext requires a non-empty string 'group_id'.")
        if not coordinator_agent_id or not isinstance(coordinator_agent_id, str):
            raise ValueError("AgentGroupContext requires a non-empty string 'coordinator_agent_id'.")
        if not agents:
            raise ValueError("AgentGroupContext requires a non-empty list of 'agents'.")

        # Defer Agent import for type check to avoid circular dependency if this file is imported early
        from autobyteus.agent.agent import Agent as AgentClassRef
        if not all(isinstance(agent, AgentClassRef) for agent in agents):
            raise TypeError("All items in 'agents' list must be instances of the 'Agent' class.")

        self.group_id: str = group_id
        self._agents_by_id: Dict[str, 'Agent'] = {agent.agent_id: agent for agent in agents}
        self._coordinator_agent_id: str = coordinator_agent_id

        if self._coordinator_agent_id not in self._agents_by_id:
            logger.error(f"Coordinator agent with ID '{self._coordinator_agent_id}' not found in the provided list of agents for group '{self.group_id}'. "
                         f"Available agent IDs: {list(self._agents_by_id.keys())}")
            # Depending on strictness, could raise ValueError here.
            # For now, logging error; get_coordinator_agent will return None.
        
        logger.info(f"AgentGroupContext initialized for group_id '{self.group_id}'. "
                    f"Total agents: {len(self._agents_by_id)}. Coordinator ID: '{self._coordinator_agent_id}'.")

    def get_agent(self, agent_id: str) -> Optional['Agent']:
        """
        Retrieves an agent from the group by its unique agent_id.

        Args:
            agent_id: The ID of the agent to retrieve.

        Returns:
            The Agent instance if found, otherwise None.
        """
        if not isinstance(agent_id, str):
            logger.warning(f"Attempted to get_agent with non-string ID: {agent_id} in group '{self.group_id}'.")
            return None
        agent = self._agents_by_id.get(agent_id)
        if not agent:
            logger.debug(f"Agent with ID '{agent_id}' not found in group '{self.group_id}'.")
        return agent

    def get_agents_by_role(self, role_name: str) -> List['Agent']:
        """
        Retrieves all agents within the group that match the specified role name.
        The role is determined from the agent's specification.

        Args:
            role_name: The role name to filter agents by.

        Returns:
            A list of Agent instances matching the role. Empty if none found.
        """
        if not isinstance(role_name, str):
            logger.warning(f"Attempted to get_agents_by_role with non-string role_name: {role_name} in group '{self.group_id}'.")
            return []
            
        matching_agents: List['Agent'] = []
        for agent in self._agents_by_id.values():
            # Assuming Agent has a 'context' attribute, and AgentContext has 'specification'
            if agent.context and agent.context.specification and agent.context.specification.role == role_name:
                matching_agents.append(agent)
        
        if not matching_agents:
            logger.debug(f"No agents found with role '{role_name}' in group '{self.group_id}'.")
        else:
            logger.debug(f"Found {len(matching_agents)} agent(s) with role '{role_name}' in group '{self.group_id}'.")
        return matching_agents

    def get_coordinator_agent(self) -> Optional['Agent']:
        """
        Retrieves the designated coordinator agent for this group.

        Returns:
            The coordinator Agent instance if found, otherwise None.
        """
        coordinator = self.get_agent(self._coordinator_agent_id)
        if not coordinator: # This might happen if ID was invalid during init
            logger.warning(f"Coordinator agent (ID: '{self._coordinator_agent_id}') not found in group '{self.group_id}'. "
                           "This might indicate an initialization issue.")
        return coordinator

    def get_all_agents(self) -> List['Agent']:
        """
        Retrieves all agents currently part of this group.

        Returns:
            A list of all Agent instances in the group.
        """
        return list(self._agents_by_id.values())

    def __repr__(self) -> str:
        return (f"<AgentGroupContext group_id='{self.group_id}', "
                f"num_agents={len(self._agents_by_id)}, "
                f"coordinator_id='{self._coordinator_agent_id}'>")
