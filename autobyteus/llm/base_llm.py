# file: autobyteus/llm/base_llm.py
from abc import ABC, abstractmethod
from autobyteus.llm.utils.cost_calculator import CostCalculator
from autobyteus.llm.utils.llm_config import LLMConfig
from autobyteus.llm.utils.rate_limiter import RateLimiter
from autobyteus.llm.utils.token_counter import TokenCounter
from autobyteus.llm.models import LLMModel

class BaseLLM(ABC):
    def __init__(self, model: LLMModel, custom_config: LLMConfig = None):
        self.model = model
        self.config = custom_config if custom_config else model.default_config
        self.rate_limiter = RateLimiter(self.config)
        #self.token_counter = TokenCounter(self.)
        #self.cost_calculator = CostCalculator(self.config, self.token_counter)

    async def send_user_message(self, user_message: str, **kwargs):
        await self.rate_limiter.wait_if_needed()
        
        #self.token_counter.add_input_tokens(user_message)

        response = await self._send_user_message_to_llm(user_message, **kwargs)

        #self.token_counter.add_output_tokens(response)

        return response
    
    """
    BaseLLM is an abstract base class that defines the common interface for all LLM integrations.
    """

    def initialize(self):
        """
        Initialize the BaseLLM object.
        """
        pass

    @abstractmethod
    async def _send_user_message_to_llm(self, user_message: str, **kwargs) -> str:
        pass


    @abstractmethod
    async def cleanup(self):
        pass

    def get_token_limit(self) -> int:
        return self.token_counter.token_limit if self.token_counter.token_limit else float('inf')

    async def send_file(self, file_path: str, **kwargs) -> str:
        # Implement file sending logic here
        pass