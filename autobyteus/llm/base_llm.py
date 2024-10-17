# file: autobyteus/llm/base_llm.py
from abc import ABC, abstractmethod
from typing import List, Optional, Union
from autobyteus.llm.utils.llm_config import LLMConfig
from autobyteus.llm.utils.rate_limiter import RateLimiter
from autobyteus.llm.models import LLMModel
class BaseLLM(ABC):
    def __init__(self, model: Union[str, LLMModel], custom_config: LLMConfig = None):
        self.model = model
        if isinstance(model, str):
            self.config = custom_config if custom_config else LLMConfig()  # Use a default config if not provided
        else:
            self.config = custom_config if custom_config else model.default_config
        self.rate_limiter = RateLimiter(self.config)

    async def send_user_message(self, user_message: str, file_paths: Optional[List[str]] = None, **kwargs):
        await self.rate_limiter.wait_if_needed()
        response = await self._send_user_message_to_llm(user_message, file_paths, **kwargs)
        return response
    
    @abstractmethod
    async def _send_user_message_to_llm(self, user_message: str, file_paths: Optional[List[str]] = None, **kwargs) -> str:
        pass

    @abstractmethod
    async def cleanup(self):
        pass

    def get_token_limit(self) -> int:
        return self.token_counter.token_limit if self.token_counter.token_limit else float('inf')