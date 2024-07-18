from repository_mongodb import BaseModel, BaseRepository
from bson import ObjectId
from datetime import datetime

class ConversationMessage(BaseModel):
    __collection_name__ = "conversation_messages"

    message_id: ObjectId = ObjectId()
    conversation_name: str
    role: str
    message: str
    timestamp: datetime = datetime.utcnow()

class ConversationMessageRepository(BaseRepository[ConversationMessage]):
    pass