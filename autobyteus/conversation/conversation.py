from typing import Optional
from autobyteus.conversation.memory.provider import MemoryProvider
from autobyteus.llm.base_llm import BaseLLM

class Conversation:
    def __init__(
        self,
        llm: BaseLLM,
        memory_provider: MemoryProvider,
        conversation_id: Optional[str] = None,
    ):
        self.llm = llm
        self.memory_provider = memory_provider
        self.conversation_id = conversation_id

    def start(self):
        self.llm.initialize()

    async def send_user_message(self, user_input: str) -> str:
        user_message_index = len(self.memory_provider.get_conversation_history()) + 1
        response = await self.llm.send_user_message(user_input, user_message_index=user_message_index)
        
        self.memory_provider.store_conversation("user", user_input)
        self.memory_provider.store_conversation("assistant", response)

        return response