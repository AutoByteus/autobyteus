from autobyteus.conversation.memory.provider import MemoryProvider

class InMemoryProvider(MemoryProvider):
    def __init__(self, conversation_id: str):
        self.conversations = []

    def store_conversation(self, role, message):
        self.conversations.append({role: message})

    def get_conversation_history(self):
        return self.conversations