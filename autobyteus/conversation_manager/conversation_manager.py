from typing import List, Optional, Union
from autobyteus.conversation_manager.conversation import Conversation
from autobyteus.llm.base_llm import BaseLLM

class ConversationManager:
    def __init__(self, llm: BaseLLM):
        self._llm = llm
        self.conversations: List[Conversation] = []
        self.current_conversation_index: int = -1 

    @property
    def llm(self) -> BaseLLM:
        """Get the current language model."""
        return self._llm
    
    async def start_conversation(self) -> Conversation:
        conversation = Conversation(self._llm)
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