# File: autobyteus/agent/group_aware_agent.py

from autobyteus.agent.agent import Agent
from autobyteus.conversation.conversation import Conversation
from autobyteus.tools.send_message_to import SendMessageTo

class GroupAwareAgent(Agent):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.agent_group = None
        self.conversation = None

    def set_agent_group(self, agent_group):
        self.agent_group = agent_group
        if not any(isinstance(tool, SendMessageTo) for tool in self.tools):
            self.tools.append(SendMessageTo(agent_group))

    async def initialize(self):
        """Initialize the agent and prepare it for receiving messages"""
        conversation_name = self._sanitize_conversation_name(self.role)
        self.conversation = await self.conversation_manager.start_conversation(
            conversation_name=conversation_name,
            llm=self.llm,
            persistence_provider_class=self.persistence_provider_class
        )

        prompt = self.prompt_builder.set_variable_value("external_tools", self._get_external_tools_section()).build()
        await self.conversation.send_user_message(prompt)

    async def receive_message(self, from_role: str, message: str):
        """Method to receive messages from other agents"""
        if not self.conversation:
            await self.initialize()
        return await self.conversation.send_user_message(f"Message from {from_role}: {message}")

    def get_description(self):
        """Return a brief description of the agent's capabilities"""
        return f"A {self.role} with capabilities: {', '.join([tool.__class__.__name__ for tool in self.tools])}"