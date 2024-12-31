
from autobyteus.llm.utils.token_counter import TokenCounter
from autobyteus.llm.utils.token_pricing_config import TokenPricingConfigRegistry
from autobyteus.llm.models import LLMModel

class TokenPriceCalculator:
    def __init__(self, model: LLMModel, token_counter: TokenCounter):
        """
        Initialize the TokenPriceCalculator with the model and token counter.
        
        Args:
            model (LLMModel): The model enum to calculate pricing for.
            token_counter (TokenCounter): The token counter containing input and output token counts.
        """
        self.token_counter = token_counter
        self.pricing = TokenPricingConfigRegistry.get_pricing(model.value)

    def calculate_input_message_price(self, text: str) -> float:
        """
        Calculate the price for the input message based on the provided text.
        
        Args:
            text (str): The input message for which to calculate the price.
            
        Returns:
            float: The price for the input message in USD.
        """
        tokens = self.token_counter.count_tokens(text)
        return (tokens / 1000) * self.pricing.input_price

    def calculate_output_message_price(self, text: str) -> float:
        """
        Calculate the price for the output message based on the provided text.
        
        Args:
            text (str): The output message for which to calculate the price.
            
        Returns:
            float: The price for the output message in USD.
        """
        tokens = self.token_counter.count_tokens(text)
        return (tokens / 1000) * self.pricing.output_price

    def calculate_cost(self) -> float:
        """
        Calculate the total cost based on input and output tokens.
        
        Returns:
            float: The total cost in USD.
        """
        input_cost = (self.token_counter.input_tokens / 1000) * self.pricing.input_price
        output_cost = (self.token_counter.output_tokens / 1000) * self.pricing.output_price
        return input_cost + output_cost
