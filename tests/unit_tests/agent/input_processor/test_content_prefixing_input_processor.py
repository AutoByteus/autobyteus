# file: autobyteus/tests/unit_tests/agent/input_processor/test_content_prefixing_input_processor.py
import pytest
from unittest.mock import MagicMock, patch

from autobyteus.agent.input_processor.content_prefixing_input_processor import ContentPrefixingInputProcessor
from autobyteus.agent.message.agent_input_user_message import AgentInputUserMessage
from autobyteus.agent.context import AgentContext 
from autobyteus.agent.context.agent_config import AgentConfig
from autobyteus.agent.events import UserMessageReceivedEvent

@pytest.fixture
def mock_agent_config() -> MagicMock:
    """Fixture for a mock AgentConfig."""
    mock_conf = MagicMock(spec=AgentConfig)
    mock_conf.name = "prefix_test_config"
    return mock_conf

@pytest.fixture
def mock_agent_context_factory(mock_agent_config: MagicMock):
    """Factory fixture to create mock AgentContext with custom_data."""
    def _factory(custom_data: dict = None): 
        mock_ctx = MagicMock(spec=AgentContext)
        mock_ctx.agent_id = "prefix_agent_789"
        mock_ctx.config = mock_agent_config
        mock_ctx.custom_data = custom_data if custom_data is not None else {} 
        return mock_ctx
    return _factory

@pytest.fixture
def sample_agent_input_user_message() -> AgentInputUserMessage:
    """Fixture for a sample AgentInputUserMessage."""
    return AgentInputUserMessage(
        content="This is the original message.",
        image_urls=["http://example.com/image.png"],
        metadata={"user_id": "user_def"}
    )

@pytest.fixture
def processor() -> ContentPrefixingInputProcessor:
    """Fixture for the ContentPrefixingInputProcessor instance."""
    return ContentPrefixingInputProcessor()

@pytest.mark.asyncio
async def test_default_prefix_used_when_no_custom_data(
    processor: ContentPrefixingInputProcessor,
    sample_agent_input_user_message: AgentInputUserMessage,
    mock_agent_context_factory
):
    """
    Tests that the default prefix is used when 'content_prefix' is not in custom_data.
    """
    mock_context = mock_agent_context_factory() 
    original_content = sample_agent_input_user_message.content
    triggering_event = UserMessageReceivedEvent(agent_input_user_message=sample_agent_input_user_message)
    
    processed_message = await processor.process(sample_agent_input_user_message, mock_context, triggering_event)
    
    expected_content = ContentPrefixingInputProcessor.DEFAULT_PREFIX + original_content
    assert processed_message.content == expected_content
    assert processed_message.image_urls == sample_agent_input_user_message.image_urls
    assert processed_message.metadata == sample_agent_input_user_message.metadata

@pytest.mark.asyncio
async def test_custom_prefix_used_from_custom_data(
    processor: ContentPrefixingInputProcessor,
    sample_agent_input_user_message: AgentInputUserMessage,
    mock_agent_context_factory
):
    """
    Tests that a custom prefix from custom_data is correctly used.
    """
    custom_prefix = "TEST_PREFIX: "
    mock_context = mock_agent_context_factory(custom_data={"content_prefix": custom_prefix})
    original_content = sample_agent_input_user_message.content
    triggering_event = UserMessageReceivedEvent(agent_input_user_message=sample_agent_input_user_message)
    
    processed_message = await processor.process(sample_agent_input_user_message, mock_context, triggering_event)
    
    expected_content = custom_prefix + original_content
    assert processed_message.content == expected_content

@pytest.mark.asyncio
async def test_default_prefix_used_if_custom_prefix_not_string(
    processor: ContentPrefixingInputProcessor,
    sample_agent_input_user_message: AgentInputUserMessage,
    mock_agent_context_factory
):
    """
    Tests that the default prefix is used if 'content_prefix' in custom_data is not a string.
    Also checks that a warning is logged.
    """
    mock_context = mock_agent_context_factory(custom_data={"content_prefix": 12345}) 
    original_content = sample_agent_input_user_message.content
    triggering_event = UserMessageReceivedEvent(agent_input_user_message=sample_agent_input_user_message)
    
    with patch('autobyteus.agent.input_processor.content_prefixing_input_processor.logger') as mock_logger:
        processed_message = await processor.process(sample_agent_input_user_message, mock_context, triggering_event)
    
    expected_content = ContentPrefixingInputProcessor.DEFAULT_PREFIX + original_content
    assert processed_message.content == expected_content
    mock_logger.warning.assert_called_once()
    call_args = mock_logger.warning.call_args[0][0]
    assert "content_prefix' in custom_data is not a string" in call_args
    assert "Using default prefix" in call_args

@pytest.mark.asyncio
async def test_empty_content_is_prefixed(
    processor: ContentPrefixingInputProcessor,
    mock_agent_context_factory
):
    """
    Tests that an empty content string is also prefixed.
    """
    message_with_empty_content = AgentInputUserMessage(content="")
    mock_context = mock_agent_context_factory() 
    triggering_event = UserMessageReceivedEvent(agent_input_user_message=message_with_empty_content)
    
    processed_message = await processor.process(message_with_empty_content, mock_context, triggering_event)
    
    assert processed_message.content == ContentPrefixingInputProcessor.DEFAULT_PREFIX

@pytest.mark.asyncio
async def test_image_urls_and_metadata_unchanged(
    processor: ContentPrefixingInputProcessor,
    sample_agent_input_user_message: AgentInputUserMessage,
    mock_agent_context_factory
):
    """
    Tests that image_urls and metadata remain unchanged by this processor.
    """
    mock_context = mock_agent_context_factory(custom_data={"content_prefix": "ANY_PREFIX: "})
    original_image_urls = list(sample_agent_input_user_message.image_urls) if sample_agent_input_user_message.image_urls else None
    original_metadata = dict(sample_agent_input_user_message.metadata)
    triggering_event = UserMessageReceivedEvent(agent_input_user_message=sample_agent_input_user_message)
    
    processed_message = await processor.process(sample_agent_input_user_message, mock_context, triggering_event)
    
    assert processed_message.image_urls == original_image_urls
    assert processed_message.metadata == original_metadata
