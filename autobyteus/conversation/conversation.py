from typing import Optional, List, Tuple
from autobyteus.conversation.persistence.provider import PersistenceProvider
from autobyteus.llm.base_llm import BaseLLM

class Conversation:
    def __init__(
        self,
        llm: BaseLLM,
        persistence_provider: Optional[PersistenceProvider] = None,
        conversation_name: Optional[str] = None,
    ):
        self.llm = llm
        self.persistence_provider = persistence_provider
        self.conversation_name = conversation_name
        self.conversation_history: List[Tuple[str, str]] = []

    def start(self):
        self.llm.initialize()

    async def send_user_message(self, user_input: str) -> str:
        user_message_index = sum(1 for entry in self.conversation_history if entry[0] == "user")

        response = await self.llm.send_user_message(user_input, user_message_index=user_message_index)
        
        self.conversation_history.append(("user", user_input))
        self.conversation_history.append(("assistant", response))

        if self.persistence_provider:
            self.persistence_provider.store_conversation("user", user_input)
            self.persistence_provider.store_conversation("assistant", response)

        return response

    def get_conversation_history(self) -> List[Tuple[str, str]]:
        if self.persistence_provider:
            return self.persistence_provider.get_conversation_history()
        return self.conversation_history