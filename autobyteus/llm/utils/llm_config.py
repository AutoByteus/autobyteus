from dataclasses import dataclass
from typing import Optional

@dataclass
class LLMConfig:
    rate_limit: Optional[int] = None  # requests per minute
    token_limit: Optional[int] = None
    system_message: Optional[str] = "You are a helpful assistant."

    @classmethod
    def default_config(cls):
        return cls()