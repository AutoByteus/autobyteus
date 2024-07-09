from autobyteus.conversation.memory.provider import MemoryProvider
from autobyteus.conversation.storage.conversation_message_repository import ConversationMessage, ConversationMessageRepository

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
        messages = self.message_repository.find_by_attributes({"conversation_id": self.conversation_id})
        return [(message.role, message.message) for message in messages]