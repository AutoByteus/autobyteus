# File: autobyteus/conversation/conversation.py
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

    async def send_user_message(self, user_input: str, file_paths: Optional[List[str]] = None) -> str:
        user_message_index = len([entry for entry in self.conversation_history if entry[0] == "user"])

        response = await self.llm.send_user_message(user_input, file_paths, user_message_index=user_message_index)
        
        # Combine user input and file paths into a single message for the conversation history
        combined_user_message = user_input
        if file_paths:
            combined_user_message += f"\n[Files sent: {', '.join(file_paths)}]"

        # Add the combined user message to the conversation history
        self.conversation_history.append(("user", combined_user_message))
        self.conversation_history.append(("assistant", response))

        if self.persistence_provider:
            self.persistence_provider.store_conversation("user", combined_user_message)
            self.persistence_provider.store_conversation("assistant", response)

        return response

    def get_conversation_history(self) -> List[Tuple[str, str]]:
        if self.persistence_provider:
            return self.persistence_provider.get_conversation_history()
        return self.conversation_history