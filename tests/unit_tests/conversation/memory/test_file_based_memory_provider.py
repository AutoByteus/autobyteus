import os
import tempfile
import pytest
from autobyteus.conversation.memory.file_based_memory_provider import FileBasedMemoryProvider

@pytest.fixture
def file_based_memory_provider():
    fd, file_path = tempfile.mkstemp()
    os.close(fd)
    yield FileBasedMemoryProvider(file_path)
    os.remove(file_path)

def test_store_conversation(file_based_memory_provider):
    file_based_memory_provider.store_conversation("user", "Hello")
    file_based_memory_provider.store_conversation("assistant", "Hi there!")

    with open(file_based_memory_provider.file_path, "r") as f:
        lines = f.readlines()
        assert len(lines) == 2
        assert lines[0].strip() == "user: Hello"
        assert lines[1].strip() == "assistant: Hi there!"

def test_get_conversation_history(file_based_memory_provider):
    file_based_memory_provider.store_conversation("user", "Hello")
    file_based_memory_provider.store_conversation("assistant", "Hi there!")

    history = file_based_memory_provider.get_conversation_history()
    assert len(history) == 2
    assert history[0] == "user: Hello"
    assert history[1] == "assistant: Hi there!"