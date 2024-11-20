from autobyteus.llm.utils.token_counter import TokenCounter
from autobyteus.llm.utils.token_pricing import TokenPricingRegistry

class CostCalculator:
    def __init__(self, model_value: str, token_counter: TokenCounter):
        self.model_value = model_value
        self.token_counter = token_counter
        self.pricing = TokenPricingRegistry.get_pricing(self.model_value)

    def calculate_cost(self) -> float:
        # Removed check for is_api_model to calculate cost for all models
        input_cost = (self.token_counter.input_tokens / 1000) * self.pricing.input_price
        output_cost = (self.token_counter.output_tokens / 1000) * self.pricing.output_price
        return round(input_cost + output_cost, 6)