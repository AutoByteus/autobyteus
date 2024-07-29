# File: autobyteus/agent/group/group_aware_agent.py

from autobyteus.agent.agent import Agent
from autobyteus.tools.send_message_to import SendMessageTo

class GroupAwareAgent(Agent):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.agent_group = None

    def set_agent_group(self, agent_group):
        self.agent_group = agent_group
        if not any(isinstance(tool, SendMessageTo) for tool in self.tools):
            self.tools.append(SendMessageTo(agent_group))

    async def receive_message(self, from_role: str, message: str):
        """Method to receive messages from other agents"""
        return await self.conversation.send_user_message(f"Message from {from_role}: {message}")

    def get_description(self):
        """Return a brief description of the agent's capabilities"""
        return f"A {self.role} with capabilities: {', '.join([tool.__class__.__name__ for tool in self.tools])}"