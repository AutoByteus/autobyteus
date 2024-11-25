from abc import ABC, abstractmethod
import datetime
from enum import Enum
from typing import List, Optional, Union
from uuid import uuid4
from autobyteus.llm.utils.cost_calculator import CostCalculator
from autobyteus.llm.utils.llm_config import LLMConfig
from autobyteus.llm.utils.messages import Message
from autobyteus.llm.utils.rate_limiter import RateLimiter
from autobyteus.llm.models import LLMModel
from autobyteus.llm.utils.token_counter import TokenCounter
import tiktoken

class BaseLLM(ABC):
    def __init__(self, model: Union[str, 'LLMModel'], custom_config: 'LLMConfig' = None):
        if isinstance(model, LLMModel):
            self.model = model.value
            self.is_api_model = getattr(model, 'is_api', True)
        else:
            self.model = model
            self.is_api_model = True  # Default to True if not provided as LLMModel instance

        self.config = custom_config if custom_config else LLMConfig()
        self.rate_limiter = RateLimiter(self.config)
        self.token_counter = TokenCounter(self.config, is_api_model=self.is_api_model)
        self.cost_calculator = CostCalculator(self.model, self.token_counter)

        # Initialize tokenizer
        tokenizer_name = self.model
        try:
            self.tokenizer = tiktoken.encoding_for_model(tokenizer_name)
        except KeyError:
            # Fallback to a default encoding
            self.tokenizer = tiktoken.get_encoding("cl100k_base")

    async def send_user_message(self, user_message: str, file_paths: Optional[List[str]] = None, conversation_id: Optional[str] = None, **kwargs):
        await self.rate_limiter.wait_if_needed()

        input_tokens = self.count_tokens(user_message)
        if not self.token_counter.add_input_tokens(input_tokens):
            raise ValueError("Input message exceeds token limit")

        # Get response from LLM
        response = await self._send_user_message_to_llm(user_message, file_paths, **kwargs)

        output_tokens = self.count_tokens(response)
        if not self.token_counter.add_output_tokens(output_tokens):
            raise ValueError("Response exceeds token limit")

        # Calculate cost
        cost = self.get_current_cost()

        return response

    def count_tokens(self, text: str) -> int:
        return len(self.tokenizer.encode(text))

    def calculate_cost(self, text: str) -> float:
        """Calculate the cost of a given text."""
        tokens = self.count_tokens(text)
        temp_token_counter = TokenCounter(self.config, is_api_model=self.is_api_model)
        temp_token_counter.add_input_tokens(tokens)
        temp_cost_calculator = CostCalculator(self.model, temp_token_counter)
        return temp_cost_calculator.calculate_cost()

    def get_current_cost(self) -> float:
        """Get the current cost of the conversation."""
        return self.cost_calculator.calculate_cost()

    def get_token_usage(self) -> dict:
        """Get the current token usage statistics."""
        return {
            'input_tokens': self.token_counter.input_tokens,
            'output_tokens': self.token_counter.output_tokens,
            'total_tokens': self.token_counter.get_total_tokens()
        }

    def reset_usage(self):
        """Reset token counter and start fresh."""
        self.token_counter.reset()

    @abstractmethod
    async def _send_user_message_to_llm(self, user_message: str, file_paths: Optional[List[str]] = None, **kwargs) -> str:
        pass

    @abstractmethod
    async def cleanup(self):
        pass

    def get_token_limit(self) -> int:
        return self.token_counter.token_limit if self.token_counter.token_limit else float('inf')