from typing import List, Optional, Type, Union
from autobyteus.conversation.conversation import Conversation
from autobyteus.llm.base_llm import BaseLLM
from autobyteus.conversation.memory import MemoryProvider  # New import

class ConversationManager:
    def __init__(
        self,
        llm: BaseLLM,
        memory_provider_class: Type[MemoryProvider],  # New argument
        conversation_name: str = None,  # New argument
    ):
        self._llm = llm
        self.conversations: List[Conversation] = []
        self.current_conversation_index: int = -1
        self.memory_provider_class = memory_provider_class  # New attribute
        self.conversation_name = conversation_name

    @property
    def llm(self) -> BaseLLM:
        """Get the current language model."""
        return self._llm

    async def start_conversation(self, conversation_name: str) -> Conversation:
        memory_provider = self.memory_provider_class(conversation_name + '#' + self.current_conversation_index)  # Create an instance of the MemoryProvider
        conversation = Conversation(self._llm, memory_provider, conversation_name)  # Pass the memory_provider and conversation_name to the Conversation constructor
        await conversation.start()
        self.conversations.append(conversation)
        self.current_conversation_index = len(self.conversations) - 1
        return conversation

    def get_current_conversation(self) -> Optional[Conversation]:
        if self.current_conversation_index >= 0:
            return self.conversations[self.current_conversation_index]
        return None

    def set_current_conversation(self, conversation: Conversation) -> None:
        if conversation in self.conversations:
            self.current_conversation_index = self.conversations.index(conversation)
        else:
            raise ValueError("Conversation not found in the list of conversations.")
