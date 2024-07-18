import pytest
from autobyteus.conversation.persistence.mongo_persistence_provider import MongoPersistenceProvider
from autobyteus.conversation.repositories.mongodb.conversation_message_repository import ConversationMessage

@pytest.fixture
def mongo_persistence_provider(mongo_database):
    persistence_provider = MongoPersistenceProvider("test_conversation")
    yield persistence_provider
    mongo_database[ConversationMessage.__collection_name__].drop()

def test_store_conversation(mongo_persistence_provider):
    mongo_persistence_provider.store_conversation("user", "Hello")
    mongo_persistence_provider.store_conversation("assistant", "Hi there!")

    messages = list(mongo_persistence_provider.message_repository.find_by_attributes({"conversation_name": "test_conversation"}))
    assert len(messages) == 2
    assert messages[0].role == "user"
    assert messages[0].message == "Hello"
    assert messages[1].role == "assistant"
    assert messages[1].message == "Hi there!"

def test_get_conversation_history(mongo_persistence_provider):
    mongo_persistence_provider.store_conversation("user", "Hello")
    mongo_persistence_provider.store_conversation("assistant", "Hi there!")

    history = mongo_persistence_provider.get_conversation_history()
    assert len(history) == 2
    assert history[0] == ("user", "Hello")
    assert history[1] == ("assistant", "Hi there!")

def test_message_id_generation(mongo_persistence_provider):
    mongo_persistence_provider.store_conversation("user", "Hello")
    messages = list(mongo_persistence_provider.message_repository.find_by_attributes({"conversation_name": "test_conversation"}))
    assert messages[0].message_id is not None