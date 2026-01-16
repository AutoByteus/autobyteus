import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from autobyteus.llm.extensions.token_usage_tracking_extension import TokenUsageTrackingExtension
from autobyteus.llm.utils.token_usage import TokenUsage
from autobyteus.llm.utils.messages import Message, MessageRole
from autobyteus.llm.utils.response_types import CompleteResponse
from autobyteus.llm.token_counter.base_token_counter import BaseTokenCounter
from autobyteus.llm.base_llm import BaseLLM

@pytest.fixture
def mock_token_counter():
    """
    Fixture to create a mock token counter.
    """
    mock = MagicMock(spec=BaseTokenCounter)
    mock.count_input_tokens.return_value = 1000
    mock.count_output_tokens.return_value = 1500
    return mock

@pytest.fixture
def mock_llm(mock_token_counter):
    """
    Fixture to create a mock LLM with a specified model and token counter.
    """
    mock_model = MagicMock()
    mock_model.provider = MagicMock()
    mock_model.provider.value = "OPENAI"
    mock_model.default_config = MagicMock()
    mock_model.default_config.pricing_config = MagicMock()
    mock_model.default_config.pricing_config.input_token_pricing = 5.0
    mock_model.default_config.pricing_config.output_token_pricing = 15.0
    
    mock_llm = MagicMock(spec=BaseLLM)
    mock_llm.model = mock_model
    mock_llm.messages = []  # Add messages list for tracking
    return mock_llm

@pytest.fixture
def token_usage_tracking_extension(mock_llm, mock_token_counter):
    """
    Fixture to create a TokenUsageTrackingExtension instance with a mock LLM.
    """
    with patch('autobyteus.llm.extensions.token_usage_tracking_extension.get_token_counter', return_value=mock_token_counter):
        extension = TokenUsageTrackingExtension(mock_llm)
    return extension

@pytest.fixture
def sample_messages():
    """
    Fixture to provide sample input and output messages.
    """
    input_message = Message(role=MessageRole.USER, content="Hello, how are you?")
    output_message = Message(role=MessageRole.ASSISTANT, content="I'm good, thank you!")
    return input_message, output_message

@pytest.mark.asyncio
async def test_token_usage_tracking_extension_basic_flow(token_usage_tracking_extension, sample_messages, mock_token_counter):
    """
    Integration test for TokenUsageTrackingExtension to verify that token usage is tracked correctly
    during a basic interaction between user and assistant.
    """
    input_message, output_message = sample_messages

    # Add the message to the LLM's message list (simulating what BaseLLM.add_user_message does)
    token_usage_tracking_extension.llm.messages.append(input_message)
    
    # Simulate adding a user message
    token_usage_tracking_extension.on_user_message_added(input_message)

    # Verify that the token counter was called for input tokens with the LLM's messages list
    mock_token_counter.count_input_tokens.assert_called_once_with([input_message])

    # Simulate generating a response
    response_content = "I'm good, thank you!"
    complete_response = CompleteResponse.from_content(response_content)
    
    # Mock the usage in the response
    complete_response.usage = TokenUsage(
        prompt_tokens=1000,
        completion_tokens=1500,
        total_tokens=2500,
        prompt_cost=(1000 / 1_000_000) * token_usage_tracking_extension.usage_tracker.pricing_config.input_token_pricing,
        completion_cost=(1500 / 1_000_000) * token_usage_tracking_extension.usage_tracker.pricing_config.output_token_pricing,
        total_cost=(1000 / 1_000_000) * token_usage_tracking_extension.usage_tracker.pricing_config.input_token_pricing +
                   (1500 / 1_000_000) * token_usage_tracking_extension.usage_tracker.pricing_config.output_token_pricing
    )

    # Simulate the after_invoke hook
    await token_usage_tracking_extension.after_invoke(
        user_message=input_message.content,
        response=complete_response
    )

    # Verify that the usage tracker was updated with the response usage
    latest_usage = token_usage_tracking_extension.latest_token_usage
    assert latest_usage is not None
    assert latest_usage.prompt_tokens == 1000
    assert latest_usage.completion_tokens == 1500
    assert latest_usage.total_tokens == 2500
    assert latest_usage.prompt_cost == (1000 / 1_000_000) * token_usage_tracking_extension.usage_tracker.pricing_config.input_token_pricing
    assert latest_usage.completion_cost == (1500 / 1_000_000) * token_usage_tracking_extension.usage_tracker.pricing_config.output_token_pricing
    assert latest_usage.total_cost == (
        (1000 / 1_000_000) * token_usage_tracking_extension.usage_tracker.pricing_config.input_token_pricing +
        (1500 / 1_000_000) * token_usage_tracking_extension.usage_tracker.pricing_config.output_token_pricing
    )

    # Verify total tokens and costs
    assert token_usage_tracking_extension.get_total_input_tokens() == 1000
    assert token_usage_tracking_extension.get_total_output_tokens() == 1500
    assert token_usage_tracking_extension.get_total_cost() == latest_usage.total_cost

    # Verify usage history
    usage_history = token_usage_tracking_extension.get_usage_history()
    assert len(usage_history) == 1
    assert usage_history[0] == latest_usage

    # Simulate adding an assistant message
    token_usage_tracking_extension.on_assistant_message_added(output_message)

    # Verify that the token counter was called for output tokens
    mock_token_counter.count_output_tokens.assert_called_once_with(output_message)

    # Verify that usage history remains consistent
    usage_history = token_usage_tracking_extension.get_usage_history()
    assert len(usage_history) == 1  # Since after_invoke updates the existing usage

    assert usage_history[0].completion_tokens == 1500
    assert usage_history[0].completion_cost == (1500 / 1_000_000) * token_usage_tracking_extension.usage_tracker.pricing_config.output_token_pricing
    assert usage_history[0].total_tokens == 2500
    assert usage_history[0].total_cost == (
        (1000 / 1_000_000) * token_usage_tracking_extension.usage_tracker.pricing_config.input_token_pricing +
        (1500 / 1_000_000) * token_usage_tracking_extension.usage_tracker.pricing_config.output_token_pricing
    )
