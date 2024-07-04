from typing import Union, Optional
from autobyteus.conversation.memory.provider import MemoryProvider
from autobyteus.llm.base_llm import BaseLLM

class Conversation:
    def __init__(
        self,
        llm: BaseLLM,
        memory_provider: MemoryProvider,  # New argument
        conversation_id: Optional[str] = None,  # New argument
    ):
        self.llm = llm
        # self.history = []  # Removed
        self.memory_provider = memory_provider  # New attribute
        self.conversation_id = conversation_id  # New attribute

    async def start(self):
        await self.llm.initialize()

    async def send_user_message(self, user_input: str) -> str:
        user_message_index = len(self.memory_provider.get_conversation_history()) + 1  # Updated
        response = await self.llm.send_user_message(user_input, user_message_index=user_message_index)

        # Store the messages in the MemoryProvider
        self.memory_provider.store_conversation("user", user_input)
        self.memory_provider.store_conversation("assistant", response)

        return response
