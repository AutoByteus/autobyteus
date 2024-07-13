import pytest
from unittest.mock import AsyncMock, MagicMock
from autobyteus.conversation.conversation import Conversation
from autobyteus.conversation.persistence.provider import PersistenceProvider
from autobyteus.llm.base_llm import BaseLLM

@pytest.fixture
def mock_llm():
    llm = MagicMock(spec=BaseLLM)
    llm.send_user_message = AsyncMock(return_value="Assistant's response")
    return llm

@pytest.fixture
def mock_persistence_provider():
    persistence_provider = MagicMock(spec=PersistenceProvider)
    persistence_provider.get_conversation_history.return_value = [
        ("user", "User message 1"),
        ("assistant", "Assistant response 1"),
        ("user", "User message 2"),
        ("assistant", "Assistant response 2"),
    ]
    return persistence_provider

@pytest.fixture
def conversation(mock_llm, mock_persistence_provider):
    return Conversation(mock_llm, mock_persistence_provider, "test_conversation")

def test_conversation_initialization(conversation, mock_llm, mock_persistence_provider):
    assert conversation.llm == mock_llm
    assert conversation.persistence_provider == mock_persistence_provider
    assert conversation.conversation_name == "test_conversation"

def test_conversation_start(conversation, mock_llm):
    conversation.start()
    mock_llm.initialize.assert_called_once()

@pytest.mark.asyncio
async def test_send_user_message_with_persistence(conversation, mock_llm, mock_persistence_provider):
    user_input = "User message 3"
    response = await conversation.send_user_message(user_input)
    assert response == "Assistant's response"
    mock_llm.send_user_message.assert_called_once_with(user_input, user_message_index=2)
    mock_persistence_provider.store_conversation.assert_any_call("user", user_input)
    mock_persistence_provider.store_conversation.assert_any_call("assistant", "Assistant's response")

@pytest.mark.asyncio
async def test_send_user_message_without_persistence(mock_llm):
    conversation = Conversation(mock_llm, conversation_name="test_conversation")
    user_input = "User message"
    response = await conversation.send_user_message(user_input)
    assert response == "Assistant's response"
    mock_llm.send_user_message.assert_called_once_with(user_input, user_message_index=0)
    assert conversation.conversation_history == [
        ("user", "User message"),
        ("assistant", "Assistant's response")
    ]

def test_get_conversation_history_with_persistence(conversation, mock_persistence_provider):
    history = conversation.get_conversation_history()
    assert history == mock_persistence_provider.get_conversation_history()

def test_get_conversation_history_without_persistence(mock_llm):
    conversation = Conversation(mock_llm, conversation_name="test_conversation")
    conversation.conversation_history = [
        ("user", "User message"),
        ("assistant", "Assistant response")
    ]
    history = conversation.get_conversation_history()
    assert history == [
        ("user", "User message"),
        ("assistant", "Assistant response")
    ]