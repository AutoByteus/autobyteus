import pytest
from autobyteus.llm.utils.llm_config import LLMConfig
from autobyteus.llm.utils.token_counter import TokenCounter
from autobyteus.llm.utils.cost_calculator import CostCalculator
from autobyteus.llm.utils.token_pricing import TokenPricingRegistry
from autobyteus.llm.models import LLMModel

@pytest.fixture
def config():
    return LLMConfig(rate_limit=10, token_limit=1000)

@pytest.fixture
def token_counter(config):
    return TokenCounter(config)

@pytest.fixture
def cost_calculator(config, token_counter):
    return CostCalculator(config, token_counter)

@pytest.mark.cost_calculator
def test_calculate_cost(cost_calculator, token_counter):
    """Test if calculate_cost computes the correct cost based on token usage."""
    token_counter.add_input_tokens("Input text. " * 100)
    token_counter.add_output_tokens("Output text. " * 50)
    
    pricing = TokenPricingRegistry.get_pricing(LLMModel.GPT_3_5_TURBO)
    expected_cost = (token_counter.input_tokens / 1000 * pricing.input_price) + \
                    (token_counter.output_tokens / 1000 * pricing.output_price)
    
    assert cost_calculator.calculate_cost() == pytest.approx(expected_cost)

@pytest.mark.cost_calculator
def test_zero_cost(cost_calculator):
    """Test if calculate_cost returns zero when no tokens have been used."""
    assert cost_calculator.calculate_cost() == 0


