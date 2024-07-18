from autobyteus.conversation.persistence.provider import PersistenceProvider
from autobyteus.conversation.repositories.mongodb.conversation_message_repository import ConversationMessage, ConversationMessageRepository

class MongoPersistenceProvider(PersistenceProvider):
    def __init__(self, conversation_name):
        self.conversation_name = conversation_name
        self.message_repository = ConversationMessageRepository()

    def store_conversation(self, role, message):
        conversation_message = ConversationMessage(
            conversation_name=self.conversation_name,
            role=role,
            message=message
        )
        self.message_repository.create(conversation_message)

    def get_conversation_history(self):
        messages = self.message_repository.find_by_attributes({"conversation_name": self.conversation_name})
        return [(message.role, message.message) for message in messages]