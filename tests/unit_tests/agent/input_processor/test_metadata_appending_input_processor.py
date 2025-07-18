# file: autobyteus/tests/unit_tests/agent/input_processor/test_metadata_appending_input_processor.py
import pytest
from unittest.mock import MagicMock

from autobyteus.agent.input_processor.metadata_appending_input_processor import MetadataAppendingInputProcessor
from autobyteus.agent.message.agent_input_user_message import AgentInputUserMessage
from autobyteus.agent.context import AgentContext 
from autobyteus.agent.context.agent_config import AgentConfig
from autobyteus.agent.events import UserMessageReceivedEvent

@pytest.fixture
def mock_agent_config() -> MagicMock:
    """Fixture for a mock AgentConfig."""
    mock_conf = MagicMock(spec=AgentConfig)
    mock_conf.name = "test_config_name_123"
    return mock_conf

@pytest.fixture
def mock_agent_context(mock_agent_config: MagicMock) -> MagicMock:
    """Fixture for a mock AgentContext."""
    mock_ctx = MagicMock(spec=AgentContext)
    mock_ctx.agent_id = "test_agent_id_abc"
    mock_ctx.config = mock_agent_config
    mock_ctx.custom_data = {} 
    return mock_ctx

@pytest.fixture
def processor() -> MetadataAppendingInputProcessor:
    """Fixture for the MetadataAppendingInputProcessor instance."""
    return MetadataAppendingInputProcessor()

@pytest.mark.asyncio
async def test_metadata_appended_to_empty_metadata(
    processor: MetadataAppendingInputProcessor,
    mock_agent_context: MagicMock
):
    """
    Tests that agent_id and config_name are appended to an empty metadata dict.
    """
    message = AgentInputUserMessage(content="Test content", metadata={})
    original_content = message.content
    original_image_urls = message.image_urls
    triggering_event = UserMessageReceivedEvent(agent_input_user_message=message)

    processed_message = await processor.process(message, mock_agent_context, triggering_event)

    assert processed_message.content == original_content, "Content should remain unchanged."
    assert processed_message.image_urls == original_image_urls, "Image URLs should remain unchanged."
    
    expected_metadata = {
        "processed_by_agent_id": mock_agent_context.agent_id,
        "processed_with_config_name": mock_agent_context.config.name
    }
    assert processed_message.metadata == expected_metadata, "Metadata should contain appended agent and config info."

@pytest.mark.asyncio
async def test_metadata_appended_to_existing_metadata(
    processor: MetadataAppendingInputProcessor,
    mock_agent_context: MagicMock
):
    """
    Tests that agent_id and config_name are appended to existing metadata,
    preserving original key-value pairs.
    """
    original_meta = {"user_id": "user123", "session_id": "session_abc"}
    message = AgentInputUserMessage(content="Test content", metadata=original_meta.copy())
    triggering_event = UserMessageReceivedEvent(agent_input_user_message=message)
    
    processed_message = await processor.process(message, mock_agent_context, triggering_event)

    assert "user_id" in processed_message.metadata
    assert processed_message.metadata["user_id"] == "user123"
    assert "session_id" in processed_message.metadata
    assert processed_message.metadata["session_id"] == "session_abc"
    
    assert "processed_by_agent_id" in processed_message.metadata
    assert processed_message.metadata["processed_by_agent_id"] == mock_agent_context.agent_id
    
    assert "processed_with_config_name" in processed_message.metadata
    assert processed_message.metadata["processed_with_config_name"] == mock_agent_context.config.name
    
    assert len(processed_message.metadata) == len(original_meta) + 2, "Metadata should have original keys plus two new ones."

@pytest.mark.asyncio
async def test_metadata_appended_when_message_metadata_is_none(
    processor: MetadataAppendingInputProcessor,
    mock_agent_context: MagicMock
):
    """
    Tests that metadata is correctly initialized and appended if message.metadata is None.
    AgentInputUserMessage constructor initializes metadata to {} if None.
    """
    message = AgentInputUserMessage(content="Test content", metadata=None)
    triggering_event = UserMessageReceivedEvent(agent_input_user_message=message)
    
    processed_message = await processor.process(message, mock_agent_context, triggering_event)
    
    expected_metadata = {
        "processed_by_agent_id": mock_agent_context.agent_id,
        "processed_with_config_name": mock_agent_context.config.name
    }
    assert processed_message.metadata == expected_metadata, "Metadata should be initialized and contain new info."

@pytest.mark.asyncio
async def test_content_and_image_urls_unchanged(
    processor: MetadataAppendingInputProcessor,
    mock_agent_context: MagicMock
):
    """
    Tests that content and image_urls are not modified by this processor.
    """
    message = AgentInputUserMessage(
        content="Some important content.",
        image_urls=["http://images.com/1.jpg"],
        metadata={"key": "value"}
    )
    original_content = message.content
    original_image_urls = list(message.image_urls) if message.image_urls else None
    triggering_event = UserMessageReceivedEvent(agent_input_user_message=message)

    processed_message = await processor.process(message, mock_agent_context, triggering_event)

    assert processed_message.content == original_content
    assert processed_message.image_urls == original_image_urls
