import pytest
from unittest.mock import AsyncMock, MagicMock
from autobyteus.conversation.conversation_manager import ConversationManager
from autobyteus.conversation.conversation import Conversation
from autobyteus.llm.base_llm import BaseLLM
from autobyteus.conversation.persistence.provider import PersistenceProvider

@pytest.fixture
def mock_llm():
    return MagicMock(spec=BaseLLM)

@pytest.fixture
def mock_persistence_provider_class():
    return MagicMock(spec=type(PersistenceProvider))

@pytest.fixture
def conversation_manager():
    return ConversationManager()

@pytest.mark.asyncio
async def test_start_conversation_with_persistence(conversation_manager, mock_llm, mock_persistence_provider_class):
    conversation = await conversation_manager.start_conversation(
        "test_conversation",
        mock_llm,
        mock_persistence_provider_class
    )
    
    assert isinstance(conversation, Conversation)
    assert conversation.conversation_name == "test_conversation"
    assert conversation.llm == mock_llm
    assert conversation.persistence_provider == mock_persistence_provider_class.return_value
    assert conversation_manager.current_conversation_index == 0
    assert len(conversation_manager.conversations) == 1

@pytest.mark.asyncio
async def test_start_conversation_without_persistence(conversation_manager, mock_llm):
    conversation = await conversation_manager.start_conversation(
        "test_conversation",
        mock_llm
    )
    
    assert isinstance(conversation, Conversation)
    assert conversation.conversation_name == "test_conversation"
    assert conversation.llm == mock_llm
    assert conversation.persistence_provider is None
    assert conversation_manager.current_conversation_index == 0
    assert len(conversation_manager.conversations) == 1

def test_get_current_conversation(conversation_manager, mock_llm):
    conversation_manager.conversations = [Conversation(mock_llm, conversation_name="test")]
    conversation_manager.current_conversation_index = 0

    current_conversation = conversation_manager.get_current_conversation()
    assert current_conversation == conversation_manager.conversations[0]

def test_get_current_conversation_empty(conversation_manager):
    assert conversation_manager.get_current_conversation() is None

def test_set_current_conversation(conversation_manager, mock_llm):
    conversation1 = Conversation(mock_llm, conversation_name="test1")
    conversation2 = Conversation(mock_llm, conversation_name="test2")
    conversation_manager.conversations = [conversation1, conversation2]

    conversation_manager.set_current_conversation(conversation2)
    assert conversation_manager.current_conversation_index == 1

    with pytest.raises(ValueError):
        conversation_manager.set_current_conversation(Conversation(mock_llm, conversation_name="test3"))