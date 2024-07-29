# File: autobyteus/agent/agent_group.py

from typing import Dict
from autobyteus.agent.group_aware_agent import GroupAwareAgent

class AgentGroup:
    def __init__(self):
        self.agents: Dict[str, GroupAwareAgent] = {}
        self.start_agent: GroupAwareAgent = None

    def add_agent(self, agent: GroupAwareAgent):
        """Add an agent to the group."""
        self.agents[agent.role] = agent
        agent.set_agent_group(self)

    def set_start_agent(self, role: str):
        """Set the starting agent for the group."""
        if role in self.agents:
            self.start_agent = self.agents[role]
        else:
            raise ValueError(f"No agent with role '{role}' found in the group.")

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

    async def run(self):
        """Start the agent group workflow by running the start agent."""
        if not self.start_agent:
            raise ValueError("Start agent not set. Use set_start_agent() to set the starting agent.")

        return await self.start_agent.run()