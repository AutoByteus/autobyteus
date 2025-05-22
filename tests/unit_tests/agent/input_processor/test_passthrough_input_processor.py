import pytest
from unittest.mock import MagicMock

from autobyteus.agent.input_processor.passthrough_input_processor import PassthroughInputProcessor
from autobyteus.agent.message.agent_input_user_message import AgentInputUserMessage
from autobyteus.agent.context import AgentContext # MODIFIED IMPORT
from autobyteus.agent.registry.agent_definition import AgentDefinition

@pytest.fixture
def mock_agent_definition() -> MagicMock:
    """Fixture for a mock AgentDefinition."""
    mock_def = MagicMock(spec=AgentDefinition)
    mock_def.name = "test_definition"
    return mock_def

@pytest.fixture
def mock_agent_context(mock_agent_definition: MagicMock) -> MagicMock:
    """Fixture for a mock AgentContext."""
    mock_ctx = MagicMock(spec=AgentContext)
    mock_ctx.agent_id = "test_agent_123"
    mock_ctx.definition = mock_agent_definition
    mock_ctx.custom_data = {}
    return mock_ctx

@pytest.fixture
def sample_agent_input_user_message() -> AgentInputUserMessage:
    """Fixture for a sample AgentInputUserMessage."""
    return AgentInputUserMessage(
        content="Hello, world!",
        image_urls=["http://example.com/image.png"],
        metadata={"user_id": "user_abc", "session_id": "session_xyz"}
    )

@pytest.fixture
def processor() -> PassthroughInputProcessor:
    """Fixture for the PassthroughInputProcessor instance."""
    return PassthroughInputProcessor()

@pytest.mark.asyncio
async def test_passthrough_processor_returns_message_unchanged(
    processor: PassthroughInputProcessor,
    sample_agent_input_user_message: AgentInputUserMessage,
    mock_agent_context: MagicMock
):
    """
    Tests that the PassthroughInputProcessor returns the message exactly as it received it.
    """
    original_content = sample_agent_input_user_message.content
    original_image_urls = list(sample_agent_input_user_message.image_urls) if sample_agent_input_user_message.image_urls else None
    original_metadata = dict(sample_agent_input_user_message.metadata)

    processed_message = await processor.process(sample_agent_input_user_message, mock_agent_context)

    assert processed_message is sample_agent_input_user_message, "Processor should return the same message instance."
    assert processed_message.content == original_content, "Content should be unchanged."
    assert processed_message.image_urls == original_image_urls, "Image URLs should be unchanged."
    assert processed_message.metadata == original_metadata, "Metadata should be unchanged."

@pytest.mark.asyncio
async def test_passthrough_processor_with_empty_message_fields(
    processor: PassthroughInputProcessor,
    mock_agent_context: MagicMock
):
    """
    Tests PassthroughInputProcessor with a message that has empty/None optional fields.
    """
    empty_message = AgentInputUserMessage(
        content="Minimal content.",
        image_urls=None,
        metadata={}
    )
    original_content = empty_message.content
    original_image_urls = empty_message.image_urls
    original_metadata = dict(empty_message.metadata)

    processed_message = await processor.process(empty_message, mock_agent_context)

    assert processed_message is empty_message
    assert processed_message.content == original_content
    assert processed_message.image_urls == original_image_urls
    assert processed_message.metadata == original_metadata
