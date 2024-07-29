# File: autobyteus/agent/agent_group.py

from typing import Dict, Optional
from autobyteus.agent.group.group_aware_agent import GroupAwareAgent
from autobyteus.agent.group.coordinator_agent import CoordinatorAgent

class AgentGroup:
    def __init__(self):
        self.agents: Dict[str, GroupAwareAgent] = {}
        self.start_agent: Optional[GroupAwareAgent] = None
        self.coordinator_agent: Optional[CoordinatorAgent] = None

    def add_agent(self, agent: GroupAwareAgent):
        """Add an agent to the group."""
        self.agents[agent.role] = agent
        agent.set_agent_group(self)

    def set_start_agent(self, agent: GroupAwareAgent):
        """Set the starting agent for the group."""
        if agent.role in self.agents:
            self.start_agent = agent
        else:
            raise ValueError(f"Agent with role '{agent.role}' not found in the group.")

    def set_coordinator_agent(self, coordinator: CoordinatorAgent):
        """Set the coordinator agent for the group."""
        self.coordinator_agent = coordinator
        self.add_agent(coordinator)
        self.start_agent = coordinator

    def get_agent(self, role: str) -> GroupAwareAgent:
        """Get an agent by its role."""
        return self.agents.get(role)

    def list_agents(self):
        """List all agent roles in the group."""
        return list(self.agents.keys())

    async def route_message(self, from_role: str, to_role: str, message: str):
        """Route a message from one agent to another."""
        target_agent = self.get_agent(to_role)
        if not target_agent:
            return f"Error: Agent with role '{to_role}' not found."

        return await target_agent.receive_message(from_role, message)

    async def initialize_agents(self):
        """Initialize all agents in the group."""
        for agent in self.agents.values():
            await agent.initialize()

    async def run(self, user_task: str = ""):
        """Start the agent group workflow by initializing all agents and running the start agent or coordinator."""
        await self.initialize_agents()

        if self.coordinator_agent:
            return await self.coordinator_agent.run(user_task)
        elif self.start_agent:
            return await self.start_agent.run()
        else:
            raise ValueError("Neither coordinator agent nor start agent set. Use set_coordinator_agent() or set_start_agent() to set an agent.")