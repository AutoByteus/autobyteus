
import pytest
from autobyteus.llm.token_counter.claude_token_counter import ClaudeTokenCounter
from autobyteus.llm.models import LLMModel

@pytest.fixture
def claude_token_counter():
    return ClaudeTokenCounter(LLMModel(name="claude-2.1"))

def test_count_tokens_empty_string(claude_token_counter):
    assert claude_token_counter.count_tokens("") == 0

def test_count_tokens_simple_text(claude_token_counter):
    text = "Hello, world!"
    token_count = claude_token_counter.count_tokens(text)
    assert token_count > 0

def test_add_input_tokens(claude_token_counter):
    text = "Hello, world!"
    claude_token_counter.add_input_tokens(text)
    assert claude_token_counter.input_tokens > 0

def test_add_output_tokens(claude_token_counter):
    text = "Hello, world!"
    claude_token_counter.add_output_tokens(text)
    assert claude_token_counter.output_tokens > 0

def test_reset_tokens(claude_token_counter):
    text = "Hello, world!"
    claude_token_counter.add_input_tokens(text)
    claude_token_counter.add_output_tokens(text)
    claude_token_counter.reset()
    assert claude_token_counter.input_tokens == 0
    assert claude_token_counter.output_tokens == 0
