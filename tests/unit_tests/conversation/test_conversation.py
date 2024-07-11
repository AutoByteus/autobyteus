import pytest
from unittest.mock import AsyncMock, MagicMock
from autobyteus.conversation.conversation import Conversation
from autobyteus.conversation.memory.provider import MemoryProvider
from autobyteus.llm.base_llm import BaseLLM

@pytest.fixture
def mock_llm():
    llm = MagicMock(spec=BaseLLM)
    llm.send_user_message = AsyncMock(return_value="Assistant's response")
    return llm

@pytest.fixture
def mock_memory_provider():
    memory_provider = MagicMock(spec=MemoryProvider)
    memory_provider.get_conversation_history.return_value = [
        ("user", "User message 1"),
        ("assistant", "Assistant response 1"),
        ("user", "User message 2"),
        ("assistant", "Assistant response 2"),
    ]
    return memory_provider

@pytest.fixture
def conversation(mock_llm, mock_memory_provider):
    return Conversation(mock_llm, mock_memory_provider, "test_conversation")

def test_conversation_initialization(conversation, mock_llm, mock_memory_provider):
    assert conversation.llm == mock_llm
    assert conversation.memory_provider == mock_memory_provider
    assert conversation.conversation_id == "test_conversation"

def test_conversation_start(conversation, mock_llm):
    conversation.start()
    mock_llm.initialize.assert_called_once()

@pytest.mark.asyncio
async def test_send_user_message(conversation, mock_llm, mock_memory_provider):
    user_input = "User message 3"
    response = await conversation.send_user_message(user_input)

    assert response == "Assistant's response"
    mock_llm.send_user_message.assert_called_once_with(user_input, user_message_index=3)
    mock_memory_provider.store_conversation.assert_any_call("user", user_input)
    mock_memory_provider.store_conversation.assert_any_call("assistant", "Assistant's response")