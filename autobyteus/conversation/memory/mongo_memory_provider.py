from autobyteus.conversation.memory.provider import MemoryProvider
from repository_mongodb import BaseModel, BaseRepository
from dataclasses import dataclass

@dataclass
class ConversationMessage(BaseModel):
    conversation_id: str
    role: str
    message: str
    __collection_name__ = "conversation_messages"

class ConversationMessageRepository(BaseRepository[ConversationMessage]):
    pass

class MongoMemoryProvider(MemoryProvider):
    def __init__(self, conversation_id):
        self.conversation_id = conversation_id
        self.message_repository = ConversationMessageRepository()

    def store_conversation(self, role, message):
        conversation_message = ConversationMessage(
            conversation_id=self.conversation_id,
            role=role,
            message=message
        )
        self.message_repository.create(conversation_message)

    def get_conversation_history(self):
        messages = self.message_repository.find({"conversation_id": self.conversation_id})
        return [(message.role, message.message) for message in messages]