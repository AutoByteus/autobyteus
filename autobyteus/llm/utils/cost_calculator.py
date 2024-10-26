from autobyteus.llm.utils.llm_config import LLMConfig
from autobyteus.llm.utils.token_counter import TokenCounter
from autobyteus.llm.utils.token_pricing import TokenPricingRegistry
from autobyteus.llm.models import LLMModel

class CostCalculator:
    def __init__(self, model: LLMModel, token_counter: TokenCounter):
        self.model = model
        self.token_counter = token_counter
        self.pricing = TokenPricingRegistry.get_pricing(model)
    
    def calculate_cost(self) -> float:
        if not self.model.is_api:
            return 0.0
            
        input_cost = (self.token_counter.input_tokens / 1000) * self.pricing.input_price
        output_cost = (self.token_counter.output_tokens / 1000) * self.pricing.output_price
        return round(input_cost + output_cost, 6)