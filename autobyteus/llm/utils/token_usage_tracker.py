from enum import Enum
from datetime import datetime
from typing import List, Optional
from autobyteus.llm.utils.messages import Message
from autobyteus.llm.models import LLMModel
from autobyteus.llm.token_counter.base_token_counter import BaseTokenCounter
from autobyteus.llm.utils.token_usage import TokenUsage

class TokenUsageTracker:
    """Tracks token usage and associated costs for an LLM"""

    def __init__(self, model: LLMModel, token_counter: BaseTokenCounter):
        """
        Initialize the TokenUsageTracker with model and token counter.
        
        Args:
            model (LLMModel): The model enum to track usage for
            token_counter (BaseTokenCounter): Counter for calculating token counts
        """
        self.token_counter = token_counter
        # Directly retrieve pricing_config from the model's default configuration
        self.pricing_config = model.default_config.pricing_config
        self._usage_history: List[TokenUsage] = []
        self.current_usage: Optional[TokenUsage] = None

    def calculate_cost(self, token_count: int, is_input: bool) -> float:
        """
        Calculate cost based on token count and type.
        Prices are in USD per million tokens.
        
        Args:
            token_count (int): Number of tokens
            is_input (bool): True if input tokens, False if output tokens
            
        Returns:
            float: Calculated cost in USD
        """
        price_per_million = (self.pricing_config.input_token_pricing 
                           if is_input 
                           else self.pricing_config.output_token_pricing)
        return (token_count / 1_000_000) * price_per_million

    def calculate_input_messages(self, messages: List[Message]) -> None:
        """Calculate token usage for input messages and initialize current usage"""
        prompt_tokens = self.token_counter.count_input_tokens(messages)
        prompt_cost = self.calculate_cost(prompt_tokens, True)
        
        self.current_usage = TokenUsage(
            prompt_tokens=prompt_tokens,
            completion_tokens=0,
            total_tokens=prompt_tokens,
            prompt_cost=prompt_cost,
            completion_cost=0.0,
            total_cost=prompt_cost
        )
        self._usage_history.append(self.current_usage)

    def calculate_output_message(self, message: Message) -> None:
        """Calculate token usage for output message and update current usage"""
        if self.current_usage is None:
            raise RuntimeError("calculate_input_messages must be called before calculate_output_message")

        completion_tokens = self.token_counter.count_output_tokens(message)
        completion_cost = self.calculate_cost(completion_tokens, False)
        
        # Update the current usage (which is already in history)
        self.current_usage.completion_tokens = completion_tokens
        self.current_usage.completion_cost = completion_cost
        self.current_usage.total_tokens = self.current_usage.prompt_tokens + completion_tokens
        self.current_usage.total_cost = self.current_usage.prompt_cost + completion_cost

        # Reset current usage after completion
        self.current_usage = None

    def get_latest_usage(self) -> Optional[TokenUsage]:
        """Get the most recent token usage record"""
        return self._usage_history[-1] if self._usage_history else None

    def get_total_input_tokens(self) -> int:
        """Get total number of input tokens used"""
        return sum(usage.prompt_tokens for usage in self._usage_history)

    def get_total_output_tokens(self) -> int:
        """Get total number of output tokens used"""
        return sum(usage.completion_tokens for usage in self._usage_history)

    def get_total_cost(self) -> float:
        """Get total cost of all token usage"""
        return sum(usage.total_cost for usage in self._usage_history)

    def get_usage_history(self) -> List[TokenUsage]:
        """Get complete usage history"""
        return self._usage_history.copy()

    def clear_history(self) -> None:
        """Clear all usage history and current usage"""
        self._usage_history.clear()
        self.current_usage = None
