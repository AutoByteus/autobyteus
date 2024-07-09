import pytest
from autobyteus.conversation.memory.mongo_memory_provider import MongoMemoryProvider
from autobyteus.conversation.storage.conversation_message_repository import ConversationMessage

@pytest.fixture
def mongo_memory_provider(mongo_database):
    memory_provider = MongoMemoryProvider("test_conversation")
    yield memory_provider
    mongo_database[ConversationMessage.__collection_name__].drop()

def test_store_conversation(mongo_memory_provider):
    mongo_memory_provider.store_conversation("user", "Hello")
    mongo_memory_provider.store_conversation("assistant", "Hi there!")

    messages = list(mongo_memory_provider.message_repository.find_by_attributes({"conversation_id": "test_conversation"}))
    assert len(messages) == 2
    assert messages[0].role == "user"
    assert messages[0].message == "Hello"
    assert messages[1].role == "assistant"
    assert messages[1].message == "Hi there!"

def test_get_conversation_history(mongo_memory_provider):
    mongo_memory_provider.store_conversation("user", "Hello")
    mongo_memory_provider.store_conversation("assistant", "Hi there!")

    history = mongo_memory_provider.get_conversation_history()
    assert len(history) == 2
    assert history[0] == ("user", "Hello")
    assert history[1] == ("assistant", "Hi there!")