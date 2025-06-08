# file: autobyteus/autobyteus/llm/utils/token_usage.py
from typing import Optional
from pydantic import BaseModel # MODIFIED: Import BaseModel

# MODIFIED: Change from dataclass to Pydantic BaseModel
class TokenUsage(BaseModel):
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    prompt_cost: Optional[float] = None
    completion_cost: Optional[float] = None
    total_cost: Optional[float] = None

    class Config:
        populate_by_name = True # If you use aliases, or for general Pydantic v2 compatibility
        # or model_config = ConfigDict(populate_by_name=True) for Pydantic v2
