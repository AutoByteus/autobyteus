import os
import tempfile
import pytest
from autobyteus.conversation.persistence.file_based_persistence_provider import FileBasedPersistenceProvider

@pytest.fixture
def file_based_persistence_provider():
    with tempfile.TemporaryDirectory() as temp_dir:
        yield FileBasedPersistenceProvider("test_conversation")

def test_store_conversation(file_based_persistence_provider):
    file_based_persistence_provider.store_conversation("user", "Hello")
    file_based_persistence_provider.store_conversation("assistant", "Hi there!")

    with open(file_based_persistence_provider.file_path, "r") as f:
        lines = f.readlines()
        assert len(lines) == 2
        assert lines[0].strip() == "user: Hello"
        assert lines[1].strip() == "assistant: Hi there!"

def test_get_conversation_history(file_based_persistence_provider):
    file_based_persistence_provider.store_conversation("user", "Hello")
    file_based_persistence_provider.store_conversation("assistant", "Hi there!")

    history = file_based_persistence_provider.get_conversation_history()
    assert len(history) == 2
    assert history[0] == "user: Hello"
    assert history[1] == "assistant: Hi there!"

def test_file_creation(file_based_persistence_provider):
    assert os.path.exists(file_based_persistence_provider.file_path)
    assert os.path.isfile(file_based_persistence_provider.file_path)