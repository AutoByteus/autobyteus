# file: autobyteus/autobyteus/llm/utils/token_usage.py
from typing import Optional
from pydantic import BaseModel, ConfigDict # MODIFIED: Import ConfigDict

# MODIFIED: Change from dataclass to Pydantic BaseModel and use model_config
class TokenUsage(BaseModel):
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    prompt_cost: Optional[float] = None
    completion_cost: Optional[float] = None
    total_cost: Optional[float] = None

    # FIX: Use model_config with ConfigDict for Pydantic v2 compatibility
    model_config = ConfigDict(
        populate_by_name=True,
    )
