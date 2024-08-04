from abc import ABC, abstractmethod
import logging
from typing import Dict, Optional
from autobyteus.agent.group.exceptions import AgentNotFoundException
from autobyteus.agent.group.group_aware_agent import GroupAwareAgent
from autobyteus.agent.group.message_types import Message
from autobyteus.events.event_emitter import EventEmitter
from autobyteus.events.event_types import EventType

logger = logging.getLogger(__name__)

class BaseAgentOrchestrator(EventEmitter, ABC):
    def __init__(self):
        super().__init__()
        self.agents: Dict[str, GroupAwareAgent] = {}  # Keyed by agent_id
        self.coordinator_agent = None

    @abstractmethod
    def add_agent(self, agent: GroupAwareAgent):
        pass

    @abstractmethod
    def get_agent(self, agent_id: str) -> Optional[GroupAwareAgent]:
        pass

    @abstractmethod
    def create_agent_if_needed(self, role: str) -> GroupAwareAgent:
        pass
    
    def set_coordinator_agent(self, agent: GroupAwareAgent):
        self.coordinator_agent = agent
        self.add_agent(agent)

    async def route_message(self, message: Message):
        target_agent = None
        if message.recipient_agent_id != "unknown":
            target_agent = self.get_agent(message.recipient_agent_id)
            if not target_agent:
                raise AgentNotFoundException(message.recipient_agent_id)
        else:
            target_agent = self.create_agent_if_needed(message.recipient_role_name)
            
        if not target_agent:
            logger.error(f"Unable to find or create agent for role: {message.recipient_role_name}")
            return None

        logger.info(f"Routing message: from={message.sender_agent_id}, to={message.recipient_role_name} (id={target_agent.agent_id})")
        return await target_agent.receive_agent_message(message)

    def start_agent(self, agent: GroupAwareAgent):
        self.add_agent(agent)
        agent.start()

    def remove_agent(self, agent_id: str):
        if agent_id in self.agents:
            agent = self.agents[agent_id]
            del self.agents[agent_id]
            logger.info(f"Agent removed: role={agent.role}, id={agent_id}")

    def handle_task_completed(self, agent_id: str):
        #self.remove_agent(agent_id)
        self.emit(EventType.TASK_COMPLETED, agent_id)

    @abstractmethod
    async def run(self):
        pass

    @abstractmethod
    async def cleanup(self):
        pass