from typing import List, Optional, Type
from autobyteus.conversation.conversation import Conversation
from autobyteus.llm.base_llm import BaseLLM
from autobyteus.conversation.persistence.provider import PersistenceProvider

class ConversationManager:
    def __init__(self):
        self.conversations: List[Conversation] = []
        self.current_conversation_index: int = -1

    async def start_conversation(
        self,
        conversation_name: str,
        llm: BaseLLM,
        persistence_provider_class: Optional[Type[PersistenceProvider]] = None,
    ) -> Conversation:
        persistence_provider = persistence_provider_class(conversation_name) if persistence_provider_class else None
        conversation = Conversation(llm, persistence_provider, conversation_name)
        conversation.start()
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