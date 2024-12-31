
from abc import ABC, abstractmethod
from typing import List, Optional, AsyncGenerator

from autobyteus.llm.utils.llm_config import LLMConfig
from autobyteus.llm.utils.rate_limiter import RateLimiter
from autobyteus.llm.token_counter.token_counter_factory import get_token_counter
from autobyteus.llm.utils.cost_calculator import TokenPriceCalculator
from autobyteus.llm.models import LLMModel

class BaseLLM(ABC):
    def __init__(self, model: LLMModel, custom_config: LLMConfig = None):
        """
        Base class for all LLMs. This sets up the configuration,
        rate limiter, token counter, and cost calculator.

        Args:
            model (LLMModel): An LLMModel enum value.
            custom_config (LLMConfig, optional): A custom config overriding the default. Defaults to None.
        """
        self.model = model
        self.config = custom_config if custom_config else model.default_config

        # Initialize the rate limiter
        self.rate_limiter = RateLimiter(self.config)

        # Initialize the provider, token counter, and cost calculator
        self._initialize_cost_calculator()

    def _initialize_cost_calculator(self):
        """
        Initializes the provider, token counter, and cost calculator based on the model.
        """
        try:
            # Initialize the token counter based on the model
            self.token_counter = get_token_counter(self.model) if self.model else None

            # Create a cost calculator attribute based on the model
            self.cost_calculator = TokenPriceCalculator(self.model, self.token_counter) if self.token_counter else None
        except Exception as e:
            # Log the error and set cost_calculator to None
            print(f"Error initializing cost calculator: {e}")
            self.cost_calculator = None

    async def send_user_message(self, user_message: str, file_paths: Optional[List[str]] = None, **kwargs):
        """
        Sends a user message to the LLM and returns the LLM's response.

        Args:
            user_message (str): The text input from the user.
            file_paths (List[str], optional): A list of file paths for additional context.
            **kwargs: Additional arguments for LLM-specific usage.

        Returns:
            str: The response from the LLM.
        """
        await self.rate_limiter.wait_if_needed()
        response = await self._send_user_message_to_llm(user_message, file_paths, **kwargs)
        return response

    async def stream_user_message(self, user_message: str, file_paths: Optional[List[str]] = None, **kwargs) -> AsyncGenerator[str, None]:
        """
        Streams the LLM response token by token.

        Args:
            user_message (str): The text input from the user.
            file_paths (List[str], optional): A list of file paths for additional context.
            **kwargs: Additional arguments for LLM-specific usage.

        Yields:
            AsyncGenerator[str, None]: Tokens from the LLM response.
        """
        await self.rate_limiter.wait_if_needed()
        async for token in self._stream_user_message_to_llm(user_message, file_paths, **kwargs):
            yield token

    @abstractmethod
    async def _send_user_message_to_llm(self, user_message: str, file_paths: Optional[List[str]] = None, **kwargs) -> str:
        """
        Abstract method for sending a user message to an LLM. Must be implemented by subclasses.
        """
        pass

    async def _stream_user_message_to_llm(self, user_message: str, file_paths: Optional[List[str]] = None, **kwargs) -> AsyncGenerator[str, None]:
        """
        Abstract method for streaming a user message response from the LLM. Must be implemented by subclasses.
        """
        pass

    async def cleanup(self):
        """
        Perform any cleanup operations. Subclasses may override this method if needed.
        """
        pass

    def get_token_limit(self) -> int:
        """
        Get the maximum token limit for the current LLM.

        Returns:
            int: The token limit or infinity if no limit is specified.
        """
        if self.token_counter and self.token_counter.token_limit:
            return self.token_counter.token_limit
        return float('inf')
