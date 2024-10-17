from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List

@dataclass
class LLMConfig:
    rate_limit: Optional[int] = None  # requests per minute
    token_limit: Optional[int] = None
    system_message: str = "You are a helpful assistant."
    temperature: float = 0.7
    max_tokens: Optional[int] = None
    top_p: Optional[float] = None
    frequency_penalty: Optional[float] = None
    presence_penalty: Optional[float] = None
    stop_sequences: Optional[List] = None
    extra_params: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def default_config(cls):
        return cls()

    def to_dict(self) -> Dict[str, Any]:
        return {k: v for k, v in self.__dict__.items() if v is not None}

    def update(self, **kwargs):
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
            else:
                self.extra_params[key] = value
