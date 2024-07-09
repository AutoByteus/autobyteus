from repository_mongodb import BaseModel, BaseRepository

class ConversationMessage(BaseModel):
    __collection_name__ = "conversation_messages"

    conversation_id: str
    role: str
    message: str

class ConversationMessageRepository(BaseRepository[ConversationMessage]):
    pass
