import pytest
from autobyteus.llm.utils.llm_config import LLMConfig
from autobyteus.llm.utils.token_counter import TokenCounter
from autobyteus.llm.models import LLMModel

@pytest.fixture
def config():
    return LLMConfig(rate_limit=10, token_limit=1000)

@pytest.fixture
def token_counter(config):
    return TokenCounter(config)

@pytest.mark.token_counter
def test_add_input_and_output_tokens(token_counter):
    """Test if add_input_tokens and add_output_tokens correctly update the token counts."""
    input_text = "User input"
    output_text = "AI response"
    
    assert token_counter.add_input_tokens(input_text)
    assert token_counter.input_tokens > 0
    assert token_counter.output_tokens == 0
    
    assert token_counter.add_output_tokens(output_text)
    assert token_counter.output_tokens > 0
    
    total_tokens = token_counter.get_total_tokens()
    assert total_tokens == token_counter.input_tokens + token_counter.output_tokens

@pytest.mark.token_counter
def test_token_limit_exceeded(token_counter):
    """Test if token limit is enforced correctly."""
    long_text = "Long text. " * 500
    
    # This should succeed and add tokens
    assert token_counter.add_input_tokens(long_text[:len(long_text)//2])
    
    # This should fail as it exceeds the token limit
    assert not token_counter.add_output_tokens(long_text)

    # The output_tokens should not have increased
    assert token_counter.output_tokens == 0

# ... (other tests remain the same)