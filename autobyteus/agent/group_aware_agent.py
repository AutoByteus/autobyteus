# File: autobyteus/agent/group_aware_agent.py

from autobyteus.agent.agent import Agent
from autobyteus.conversation.conversation import Conversation
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
        conversation: Conversation = await self.conversation_manager.get_current_conversation()
        return await conversation.send_user_message(f"Message from {from_role}: {message}")