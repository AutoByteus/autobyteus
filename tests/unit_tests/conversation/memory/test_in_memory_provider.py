import pytest
from autobyteus.conversation.memory.in_memory_provider import InMemoryProvider

@pytest.fixture
def in_memory_provider():
    return InMemoryProvider("test_conversation")

def test_store_conversation(in_memory_provider):
    in_memory_provider.store_conversation("user", "Hello")
    in_memory_provider.store_conversation("assistant", "Hi there!")

    expected_conversations = [
        {"user": "Hello"},
        {"assistant": "Hi there!"}
    ]
    assert in_memory_provider.get_conversation_history() == expected_conversations

def test_get_conversation_history(in_memory_provider):
    in_memory_provider.store_conversation("user", "Message 1")
    in_memory_provider.store_conversation("assistant", "Response 1")
    in_memory_provider.store_conversation("user", "Message 2")
    in_memory_provider.store_conversation("assistant", "Response 2")

    expected_conversations = [
        {"user": "Message 1"},
        {"assistant": "Response 1"},
        {"user": "Message 2"},
        {"assistant": "Response 2"}
    ]
    assert in_memory_provider.get_conversation_history() == expected_conversations