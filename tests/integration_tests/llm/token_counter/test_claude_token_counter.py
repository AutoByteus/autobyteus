
import pytest
from autobyteus.llm.token_counter.claude_token_counter import ClaudeTokenCounter
from autobyteus.llm.models import LLMModel
from autobyteus.llm.utils.messages import Message, MessageRole

@pytest.fixture
def claude_token_counter():
    return ClaudeTokenCounter(LLMModel.CLAUDE_3_5_SONNET_API)

@pytest.fixture
def sample_messages():
    return [
        Message(role=MessageRole.SYSTEM, content="You are a helpful assistant."),
        Message(role=MessageRole.USER, content="Hello, world!"),
        Message(role=MessageRole.ASSISTANT, content="Hi! How can I help you today?")
    ]

@pytest.fixture
def single_message():
    return Message(role=MessageRole.USER, content="Hello, world!")

def test_convert_to_internal_format(claude_token_counter, sample_messages):
    processed_messages = claude_token_counter.convert_to_internal_format(sample_messages)
    assert len(processed_messages) == len(sample_messages)
    assert all(isinstance(msg, str) for msg in processed_messages)
    assert processed_messages[0].startswith(f"{MessageRole.SYSTEM.value}:")
    assert processed_messages[1].startswith(f"{MessageRole.USER.value}:")
    assert processed_messages[2].startswith(f"{MessageRole.ASSISTANT.value}:")

def test_count_input_tokens_empty_list(claude_token_counter):
    assert claude_token_counter.count_input_tokens([]) == 0

def test_count_input_tokens_single_message(claude_token_counter, single_message):
    token_count = claude_token_counter.count_input_tokens([single_message])
    assert token_count > 0

def test_count_input_tokens_multiple_messages(claude_token_counter, sample_messages):
    token_count = claude_token_counter.count_input_tokens(sample_messages)
    assert token_count > 0

def test_count_output_tokens_empty_message(claude_token_counter):
    empty_message = Message(role=MessageRole.ASSISTANT, content="")
    assert claude_token_counter.count_output_tokens(empty_message) == 0

def test_count_output_tokens_with_content(claude_token_counter, single_message):
    token_count = claude_token_counter.count_output_tokens(single_message)
    assert token_count > 0

def test_count_input_tokens_error_handling(claude_token_counter):
    invalid_message = Message(role=MessageRole.USER, content=None)
    with pytest.raises(ValueError):
        claude_token_counter.count_input_tokens([invalid_message])

def test_count_output_tokens_error_handling(claude_token_counter):
    invalid_message = Message(role=MessageRole.ASSISTANT, content=None)
    with pytest.raises(ValueError):
        claude_token_counter.count_output_tokens(invalid_message)

def test_total_tokens_calculation(claude_token_counter, sample_messages, single_message):
    input_tokens = claude_token_counter.count_input_tokens(sample_messages)
    output_tokens = claude_token_counter.count_output_tokens(single_message)
    total_tokens = claude_token_counter.get_total_tokens(input_tokens, output_tokens)
    assert total_tokens == input_tokens + output_tokens
