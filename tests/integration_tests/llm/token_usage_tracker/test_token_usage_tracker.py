import pytest
from unittest.mock import MagicMock
from datetime import datetime
from autobyteus.llm.models import LLMModel
from autobyteus.llm.utils.llm_config import TokenPricingConfig
from autobyteus.llm.token_counter.base_token_counter import BaseTokenCounter
from autobyteus.llm.utils.token_usage_tracker import TokenUsageTracker, TokenUsage
from autobyteus.llm.utils.messages import Message, MessageRole
from autobyteus.llm.utils.response_types import CompleteResponse, ChunkResponse


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
def token_usage_tracker(mock_token_counter):
    """
    Fixture to create a TokenUsageTracker with a mock token counter.
    """
    model = LLMModel.GPT_3_5_TURBO_API
    tracker = TokenUsageTracker(model, mock_token_counter)
    return tracker


@pytest.fixture
def sample_messages():
    """
    Fixture to provide sample input and output messages.
    """
    input_messages = [
        Message(role=MessageRole.SYSTEM, content="System message"),
        Message(role=MessageRole.USER, content="User message 1"),
        Message(role=MessageRole.USER, content="User message 2")
    ]
    output_message = Message(role=MessageRole.ASSISTANT, content="Assistant response")
    return input_messages, output_message


def test_initial_state(token_usage_tracker):
    """
    Test that the initial state of the tracker has no usage history.
    """
    assert token_usage_tracker.get_usage_history() == []
    assert token_usage_tracker.get_total_input_tokens() == 0
    assert token_usage_tracker.get_total_output_tokens() == 0
    assert token_usage_tracker.get_total_cost() == 0.0


def test_calculate_input_usage(token_usage_tracker, sample_messages):
    """
    Test calculating input token usage.
    """
    input_messages, _ = sample_messages
    token_usage_tracker.calculate_input_messages(input_messages)
    
    usage_history = token_usage_tracker.get_usage_history()
    assert len(usage_history) == 1
    usage = usage_history[0]
    assert usage.prompt_tokens == 1000
    assert usage.completion_tokens == 0
    assert usage.total_tokens == 1000
    
    pricing = LLMModel.GPT_3_5_TURBO_API.default_config.pricing_config
    expected_prompt_cost = (1000 / 1_000_000) * pricing.input_token_pricing
    assert usage.prompt_cost == expected_prompt_cost
    assert usage.completion_cost == 0.0
    assert usage.total_cost == expected_prompt_cost
    
    assert token_usage_tracker.get_total_input_tokens() == 1000
    assert token_usage_tracker.get_total_cost() == expected_prompt_cost


def test_calculate_output_usage(token_usage_tracker, sample_messages):
    """
    Test calculating output token usage.
    """
    input_messages, output_message = sample_messages
    token_usage_tracker.calculate_input_messages(input_messages)
    token_usage_tracker.calculate_output_message(output_message)
    
    usage_history = token_usage_tracker.get_usage_history()
    assert len(usage_history) == 1
    usage = usage_history[0]
    assert usage.prompt_tokens == 1000
    assert usage.completion_tokens == 1500
    assert usage.total_tokens == 2500
    
    pricing = LLMModel.GPT_3_5_TURBO_API.default_config.pricing_config
    expected_prompt_cost = (1000 / 1_000_000) * pricing.input_token_pricing
    expected_completion_cost = (1500 / 1_000_000) * pricing.output_token_pricing
    
    assert usage.prompt_cost == expected_prompt_cost
    assert usage.completion_cost == expected_completion_cost
    assert usage.total_cost == expected_prompt_cost + expected_completion_cost
    
    assert token_usage_tracker.get_total_output_tokens() == 1500
    assert token_usage_tracker.get_total_cost() == expected_prompt_cost + expected_completion_cost


def test_calculate_both_input_and_output_usage(token_usage_tracker, sample_messages):
    """
    Test calculating both input and output token usage.
    """
    input_messages, output_message = sample_messages
    token_usage_tracker.calculate_input_messages(input_messages)
    token_usage_tracker.calculate_output_message(output_message)
    
    usage_history = token_usage_tracker.get_usage_history()
    assert len(usage_history) == 1
    
    usage = usage_history[0]
    assert usage.prompt_tokens == 1000
    assert usage.completion_tokens == 1500
    assert usage.total_tokens == 2500
    
    pricing = LLMModel.GPT_3_5_TURBO_API.default_config.pricing_config
    expected_prompt_cost = (1000 / 1_000_000) * pricing.input_token_pricing
    expected_completion_cost = (1500 / 1_000_000) * pricing.output_token_pricing
    
    assert usage.prompt_cost == expected_prompt_cost
    assert usage.completion_cost == expected_completion_cost
    assert usage.total_cost == expected_prompt_cost + expected_completion_cost
    
    assert token_usage_tracker.get_total_input_tokens() == 1000
    assert token_usage_tracker.get_total_output_tokens() == 1500
    assert token_usage_tracker.get_total_cost() == expected_prompt_cost + expected_completion_cost


def test_clear_history(token_usage_tracker, sample_messages):
    """
    Test clearing the usage history.
    """
    input_messages, output_message = sample_messages
    token_usage_tracker.calculate_input_messages(input_messages)
    token_usage_tracker.calculate_output_message(output_message)
    
    assert len(token_usage_tracker.get_usage_history()) == 1
    token_usage_tracker.clear_history()
    
    assert token_usage_tracker.get_usage_history() == []
    assert token_usage_tracker.get_total_input_tokens() == 0
    assert token_usage_tracker.get_total_output_tokens() == 0
    assert token_usage_tracker.get_total_cost() == 0.0


def test_multiple_usages(token_usage_tracker, sample_messages):
    """
    Test multiple input and output usages.
    """
    input_messages, output_message = sample_messages
    token_usage_tracker.calculate_input_messages(input_messages)
    token_usage_tracker.calculate_output_message(output_message)
    
    # Simulate another round of usage
    token_usage_tracker.calculate_input_messages(input_messages)
    token_usage_tracker.calculate_output_message(output_message)
    
    usage_history = token_usage_tracker.get_usage_history()
    assert len(usage_history) == 2
    
    pricing = LLMModel.GPT_3_5_TURBO_API.default_config.pricing_config
    
    # First usage
    first_usage = usage_history[0]
    assert first_usage.prompt_tokens == 1000
    assert first_usage.completion_tokens == 1500
    expected_first_prompt_cost = (1000 / 1_000_000) * pricing.input_token_pricing
    expected_first_completion_cost = (1500 / 1_000_000) * pricing.output_token_pricing
    assert first_usage.prompt_cost == expected_first_prompt_cost
    assert first_usage.completion_cost == expected_first_completion_cost
    assert first_usage.total_cost == expected_first_prompt_cost + expected_first_completion_cost
    
    # Second usage
    second_usage = usage_history[1]
    assert second_usage.prompt_tokens == 1000
    assert second_usage.completion_tokens == 1500
    expected_second_prompt_cost = (1000 / 1_000_000) * pricing.input_token_pricing
    expected_second_completion_cost = (1500 / 1_000_000) * pricing.output_token_pricing
    assert second_usage.prompt_cost == expected_second_prompt_cost
    assert second_usage.completion_cost == expected_second_completion_cost
    assert second_usage.total_cost == expected_second_prompt_cost + expected_second_completion_cost
    
    # Total tokens and costs
    total_input_tokens = 1000 * 2
    total_output_tokens = 1500 * 2
    expected_total_cost = (expected_first_prompt_cost + expected_first_completion_cost) + (expected_second_prompt_cost + expected_second_completion_cost)
    
    assert token_usage_tracker.get_total_input_tokens() == total_input_tokens
    assert token_usage_tracker.get_total_output_tokens() == total_output_tokens
    assert token_usage_tracker.get_total_cost() == expected_total_cost


def test_default_pricing(token_usage_tracker, sample_messages):
    """
    Test that the default pricing is used when model is not found.
    """
    # Create a tracker with a model that doesn't exist in the pricing config
    unknown_model = LLMModel("UNKNOWN_MODEL_API")
    token_usage_tracker_unknown = TokenUsageTracker(unknown_model, token_usage_tracker.token_counter)
    
    input_messages, output_message = sample_messages
    token_usage_tracker_unknown.calculate_input_messages(input_messages)
    token_usage_tracker_unknown.calculate_output_message(output_message)
    
    usage_history = token_usage_tracker_unknown.get_usage_history()
    assert len(usage_history) == 1
    
    usage = usage_history[0]
    
    # Since unknown_model won't have proper pricing, default pricing should be 0.0
    assert usage.prompt_cost == 0.0
    assert usage.completion_cost == 0.0
    assert usage.total_cost == 0.0
    
    assert token_usage_tracker_unknown.get_total_cost() == 0.0


def test_zero_tokens(token_usage_tracker):
    """
    Test handling of zero tokens.
    """
    empty_input = []
    empty_output = Message(role=MessageRole.ASSISTANT, content="")
    
    token_usage_tracker.calculate_input_messages(empty_input)
    token_usage_tracker.calculate_output_message(empty_output)
    
    usage_history = token_usage_tracker.get_usage_history()
    assert len(usage_history) == 1
    
    usage = usage_history[0]
    assert usage.prompt_tokens == 1000  # Mock returns 1000 even for empty input
    assert usage.completion_tokens == 1500  # Mock returns 1500 even for empty output
    assert usage.total_tokens == 2500
    
    pricing = LLMModel.GPT_3_5_TURBO_API.default_config.pricing_config
    expected_prompt_cost = (1000 / 1_000_000) * pricing.input_token_pricing
    expected_completion_cost = (1500 / 1_000_000) * pricing.output_token_pricing
    expected_total_cost = expected_prompt_cost + expected_completion_cost
    
    assert usage.prompt_cost == expected_prompt_cost
    assert usage.completion_cost == expected_completion_cost
    assert usage.total_cost == expected_total_cost
    
    assert token_usage_tracker.get_total_input_tokens() == 1000
    assert token_usage_tracker.get_total_output_tokens() == 1500
    assert token_usage_tracker.get_total_cost() == expected_total_cost


def test_partial_history(token_usage_tracker, sample_messages):
    """
    Test retrieving latest usage when history is partially filled.
    """
    input_messages, _ = sample_messages
    token_usage_tracker.calculate_input_messages(input_messages)
    
    usage_history = token_usage_tracker.get_usage_history()
    assert len(usage_history) == 1
    
    usage = usage_history[0]
    assert usage.prompt_tokens == 1000
    assert usage.completion_tokens == 0
    assert usage.total_tokens == 1000
    pricing = LLMModel.GPT_3_5_TURBO_API.default_config.pricing_config
    assert usage.prompt_cost == (1000 / 1_000_000) * pricing.input_token_pricing
    assert usage.completion_cost == 0.0
    assert usage.total_cost == usage.prompt_cost


def test_complete_response_integration(token_usage_tracker, sample_messages):
    """
    Test integration with CompleteResponse to ensure usage is tracked correctly.
    """
    input_messages, output_message = sample_messages
    token_usage_tracker.calculate_input_messages(input_messages)
    token_usage_tracker.calculate_output_message(output_message)
    
    complete_response = CompleteResponse.from_content(output_message.content)
    complete_response.usage = token_usage_tracker.get_usage_history()[-1]
    
    pricing = LLMModel.GPT_3_5_TURBO_API.default_config.pricing_config
    assert complete_response.usage is not None
    assert complete_response.usage.completion_tokens == 1500
    assert complete_response.usage.completion_cost == (1500 / 1_000_000) * pricing.output_token_pricing
    assert complete_response.usage.total_tokens == 2500
    assert complete_response.usage.total_cost == (
        (1000 / 1_000_000) * pricing.input_token_pricing +
        (1500 / 1_000_000) * pricing.output_token_pricing
    )


def test_chunk_response_handling(token_usage_tracker, sample_messages):
    """
    Test handling of ChunkResponse to ensure partial usage tracking.
    """
    input_messages, _ = sample_messages
    token_usage_tracker.calculate_input_messages(input_messages)
    
    pricing = LLMModel.GPT_3_5_TURBO_API.default_config.pricing_config
    
    # Simulate receiving a chunk of the output
    chunk1 = ChunkResponse(content="Assistant part 1", is_complete=False)
    chunk1.usage = TokenUsage(
        prompt_tokens=0,
        completion_tokens=750,
        total_tokens=750,
        prompt_cost=0.0,
        completion_cost=(750 / 1_000_000) * pricing.output_token_pricing,
        total_cost=(750 / 1_000_000) * pricing.output_token_pricing
    )
    token_usage_tracker._usage_history.append(chunk1.usage)
    
    assert token_usage_tracker.get_total_output_tokens() == 750
    assert token_usage_tracker.get_total_cost() == (
        (1000 / 1_000_000) * pricing.input_token_pricing +
        chunk1.usage.total_cost
    )
    
    # Simulate receiving the final chunk of the output
    chunk2 = ChunkResponse(content="Assistant part 2", is_complete=True)
    chunk2.usage = TokenUsage(
        prompt_tokens=0,
        completion_tokens=750,
        total_tokens=750,
        prompt_cost=0.0,
        completion_cost=(750 / 1_000_000) * pricing.output_token_pricing,
        total_cost=(750 / 1_000_000) * pricing.output_token_pricing
    )
    token_usage_tracker._usage_history.append(chunk2.usage)
    
    assert token_usage_tracker.get_total_output_tokens() == 1500
    assert token_usage_tracker.get_total_cost() == (
        (1000 / 1_000_000) * pricing.input_token_pricing +
        chunk1.usage.total_cost +
        chunk2.usage.total_cost
    )
    
    latest_output = token_usage_tracker.get_usage_history()[-1]
    assert latest_output.completion_tokens == 750
    assert latest_output.completion_cost == (750 / 1_000_000) * pricing.output_token_pricing
