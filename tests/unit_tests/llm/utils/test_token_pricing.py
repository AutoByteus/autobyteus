import pytest
from autobyteus.llm.utils.token_pricing import TokenPricingRegistry
from autobyteus.llm.models import LLMModel

@pytest.mark.token_pricing
@pytest.mark.parametrize("model,expected_input_price,expected_output_price", [
    (LLMModel.GPT_3_5_TURBO, 0.0015, 0.002),
    (LLMModel.GPT_4, 0.03, 0.06),
    (LLMModel.CLAUDE_3_HAIKU, 0.0015, 0.002),
])
def test_get_pricing_known_model(model, expected_input_price, expected_output_price):
    """Test if get_pricing returns correct pricing for known models."""
    pricing = TokenPricingRegistry.get_pricing(model)
    assert pricing.input_price == expected_input_price
    assert pricing.output_price == expected_output_price

@pytest.mark.token_pricing
def test_get_pricing_unknown_model():
    """Test if get_pricing returns zero pricing for unknown models."""
    class UnknownModel(LLMModel):
        UNKNOWN = "unknown-model"

    pricing = TokenPricingRegistry.get_pricing(UnknownModel.UNKNOWN)
    assert pricing.input_price == 0
    assert pricing.output_price == 0