
from dataclasses import dataclass
from typing import Optional

@dataclass
class TokenUsage:
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    prompt_cost: Optional[float] = None
    completion_cost: Optional[float] = None
    total_cost: Optional[float] = None

