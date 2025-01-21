from dataclasses import dataclass, field, asdict
from typing import Optional, Dict, Any, List
import json

@dataclass
class TokenPricingConfig:
    input_token_pricing: float = 0.0
    output_token_pricing: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert TokenPricingConfig to dictionary"""
        return {
            'input_token_pricing': self.input_token_pricing,
            'output_token_pricing': self.output_token_pricing
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TokenPricingConfig':
        """Create TokenPricingConfig from dictionary"""
        return cls(
            input_token_pricing=data.get('input_token_pricing', 0.0),
            output_token_pricing=data.get('output_token_pricing', 0.0)
        )

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
    pricing_config: TokenPricingConfig = field(default_factory=TokenPricingConfig)

    @classmethod
    def default_config(cls):
        return cls()

    def to_dict(self) -> Dict[str, Any]:
        """Convert LLMConfig to dictionary"""
        config_dict = asdict(self)
        # Convert TokenPricingConfig to dict explicitly
        config_dict['pricing_config'] = self.pricing_config.to_dict()
        # Remove None values
        return {k: v for k, v in config_dict.items() if v is not None}

    def to_json(self) -> str:
        """Convert LLMConfig to JSON string"""
        return json.dumps(self.to_dict())

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'LLMConfig':
        """Create LLMConfig from dictionary"""
        # Handle pricing_config separately
        pricing_config_data = data.pop('pricing_config', {})
        pricing_config = TokenPricingConfig.from_dict(pricing_config_data)
        
        # Create new instance with remaining data
        config = cls(
            rate_limit=data.get('rate_limit'),
            token_limit=data.get('token_limit'),
            system_message=data.get('system_message', "You are a helpful assistant."),
            temperature=data.get('temperature', 0.7),
            max_tokens=data.get('max_tokens'),
            top_p=data.get('top_p'),
            frequency_penalty=data.get('frequency_penalty'),
            presence_penalty=data.get('presence_penalty'),
            stop_sequences=data.get('stop_sequences'),
            extra_params=data.get('extra_params', {}),
            pricing_config=pricing_config
        )
        return config

    @classmethod
    def from_json(cls, json_str: str) -> 'LLMConfig':
        """Create LLMConfig from JSON string"""
        data = json.loads(json_str)
        return cls.from_dict(data)

    def update(self, **kwargs):
        """Update config with new values"""
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
            else:
                self.extra_params[key] = value
