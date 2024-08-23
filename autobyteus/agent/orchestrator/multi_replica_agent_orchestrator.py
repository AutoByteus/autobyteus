import logging
from typing import Dict, List, Optional
from autobyteus.agent.factory.agent_factory import AgentFactory
from autobyteus.agent.group.group_aware_agent import GroupAwareAgent
from autobyteus.agent.orchestrator.base_agent_orchestrator import BaseAgentOrchestrator

logger = logging.getLogger(__name__)

class MultiReplicaAgentOrchestrator(BaseAgentOrchestrator):
    def __init__(self):
        super().__init__()
        self.role_to_ids: Dict[str, List[str]] = {}  # Mapping from role to list of agent_ids
        self.role_counters: Dict[str, int] = {}  # Counter for each role to generate unique IDs
        self.agent_factories: Dict[str, AgentFactory] = {}  # Keyed by agent role

    def add_agent_factory(self, agent_factory: AgentFactory):
        self.agent_factories[agent_factory.role] = agent_factory
        logger.info(f"AgentFactory added for role: {agent_factory.role}")

    def generate_agent_id(self, role: str) -> str:
        if role not in self.role_counters:
            self.role_counters[role] = 0
        self.role_counters[role] += 1
        return f"{role}_{self.role_counters[role]:03d}"

    def add_agent(self, agent: GroupAwareAgent):
        self.agents[agent.id] = agent
        if agent.role not in self.role_to_ids:
            self.role_to_ids[agent.role] = []
        self.role_to_ids[agent.role].append(agent.id)
        agent.set_agent_orchestrator(self)
        logger.info(f"Agent added to orchestrator: role={agent.role}, id={agent.id}")

    def get_agent(self, agent_id: str) -> Optional[GroupAwareAgent]:
        return self.agents.get(agent_id)

    def create_agent_if_needed(self, role: str) -> GroupAwareAgent:
        idle_agent = self.get_idle_agent(role)
        if idle_agent:
            return idle_agent

        if role not in self.agent_factories:
            raise ValueError(f"AgentFactory for role '{role}' not found. Use add_agent_factory() to add an AgentFactory.")
        
        agent_factory = self.agent_factories[role]
        agent_id = self.generate_agent_id(role)
        new_agent = agent_factory.create_agent(agent_id)
        self.add_agent(new_agent)
        logger.info(f"New agent created: role={role}, id={new_agent.id}")
        return new_agent

    def get_idle_agent(self, role: str) -> Optional[GroupAwareAgent]:
        for agent_id in self.role_to_ids.get(role, []):
            agent = self.agents[agent_id]
            if agent.status == "idle":  # Assuming there's a status attribute in GroupAwareAgent
                return agent
        return None

    async def run(self):
        if not self.coordinator_agent:
            raise ValueError("Coordinator agent not set. Use set_coordinator_agent() to set a coordinator.")
        
        logger.info(f"Starting multi-agent workflow with coordinator: role={self.coordinator_agent.role}, id={self.coordinator_agent.agent_id}")
        result = await self.coordinator_agent.run()
        logger.info("Multi-agent workflow completed")
        return result

    async def cleanup(self):
        logger.info("Starting cleanup for all agents in the orchestrator")
        for agent in self.agents.values():
            await agent.cleanup()
        logger.info("Cleanup completed for all agents in the orchestrator")