import logging
from typing import Dict, Optional
from autobyteus.agent.group.group_aware_agent import GroupAwareAgent
from autobyteus.agent.orchestrator.base_agent_orchestrator import BaseAgentOrchestrator

logger = logging.getLogger(__name__)

class SingleReplicaAgentOrchestrator(BaseAgentOrchestrator):
    def __init__(self):
        super().__init__()
        self.role_to_agent: Dict[str, GroupAwareAgent] = {}

    def add_agent(self, agent: GroupAwareAgent):
        if agent.role in self.role_to_agent:
            logger.warning(f"Replacing existing agent for role: {agent.role}")
        self.agents[agent.agent_id] = agent
        self.role_to_agent[agent.role] = agent
        agent.set_agent_orchestrator(self)
        logger.info(f"Agent added to orchestrator: role={agent.role}, agent_id={agent.agent_id}")

    def get_agent(self, agent_id: str) -> Optional[GroupAwareAgent]:
        return self.agents.get(agent_id)

    def create_agent_if_needed(self, role: str) -> GroupAwareAgent:
        if role in self.role_to_agent:
            return self.role_to_agent[role]
        else:
            raise ValueError(f"Agent for role '{role}' not found. Use add_agent() to add an agent for this role.")

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