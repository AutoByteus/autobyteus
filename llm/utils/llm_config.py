from dataclasses import dataclass, field, asdict, fields
from typing import Optional, Dict, Any, List
import json
import logging 

logger = logging.getLogger(__name__) 

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

    def __post_init__(self):
        """
        Ensures that pricing_config is always an instance of TokenPricingConfig.
        This is crucial if LLMConfig is initialized with a dictionary for pricing_config
        (e.g., when unpacking a dict created by a previous to_dict() call).
        """
        if isinstance(self.pricing_config, dict):
            logger.debug(f"LLMConfig __post_init__: pricing_config is a dict, converting. Value: {self.pricing_config}")
            self.pricing_config = TokenPricingConfig.from_dict(self.pricing_config)
        elif not isinstance(self.pricing_config, TokenPricingConfig):
            logger.warning(
                f"LLMConfig __post_init__: pricing_config was initialized with an unexpected type: {type(self.pricing_config)}. "
                f"Value: {self.pricing_config}. Resetting to default TokenPricingConfig."
            )
            self.pricing_config = TokenPricingConfig()
        else:
            logger.debug(f"LLMConfig __post_init__: pricing_config is already TokenPricingConfig. Value: {self.pricing_config}")


    @classmethod
    def default_config(cls):
        return cls()

    def to_dict(self) -> Dict[str, Any]:
        """Convert LLMConfig to dictionary."""
        # Defensively ensure self.pricing_config is a TokenPricingConfig object
        # This check acts as a safeguard if __post_init__ somehow didn't set it correctly.
        if isinstance(self.pricing_config, dict):
            logger.warning(
                f"LLMConfig.to_dict(): self.pricing_config found as dict. Value: {self.pricing_config}. "
                "This indicates __post_init__ might not have run or its effect was undone. Converting now."
            )
            try:
                self.pricing_config = TokenPricingConfig.from_dict(self.pricing_config)
            except Exception as e:
                logger.error(f"LLMConfig.to_dict(): Critical error converting pricing_config dict to object: {e}. "
                               f"Proceeding with pricing_config as potentially incorrect dict or empty.")
                # If conversion fails, self.pricing_config remains a dict.
                # The subsequent call to self.pricing_config.to_dict() would fail if not handled.

        data = {}
        for f in fields(self):  # Use dataclasses.fields to iterate
            field_value = getattr(self, f.name)
            if f.name == 'pricing_config':
                if isinstance(self.pricing_config, TokenPricingConfig):
                    data[f.name] = self.pricing_config.to_dict()
                elif isinstance(self.pricing_config, dict): # Fallback if it's still a dict
                    data[f.name] = self.pricing_config 
                else: # Should not happen
                    logger.error(f"LLMConfig.to_dict(): pricing_config has unexpected type {type(self.pricing_config)} after checks.")
                    data[f.name] = {} # Default to empty dict
            else:
                data[f.name] = field_value
        
        return {k: v for k, v in data.items() if v is not None}


    def to_json(self) -> str:
        """Convert LLMConfig to JSON string"""
        return json.dumps(self.to_dict())

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'LLMConfig':
        """Create LLMConfig from dictionary"""
        # Make a copy to avoid modifying the input dictionary
        data_copy = data.copy()
        pricing_config_data = data_copy.pop('pricing_config', {})
        
        # The __post_init__ method will handle the conversion of pricing_config_data (dict)
        # to a TokenPricingConfig object.
        config = cls(
            rate_limit=data_copy.get('rate_limit'),
            token_limit=data_copy.get('token_limit'),
            system_message=data_copy.get('system_message', "You are a helpful assistant."),
            temperature=data_copy.get('temperature', 0.7),
            max_tokens=data_copy.get('max_tokens'),
            top_p=data_copy.get('top_p'),
            frequency_penalty=data_copy.get('frequency_penalty'),
            presence_penalty=data_copy.get('presence_penalty'),
            stop_sequences=data_copy.get('stop_sequences'),
            extra_params=data_copy.get('extra_params', {}),
            pricing_config=pricing_config_data 
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
                if key == 'pricing_config' and isinstance(value, dict):
                    self.pricing_config = TokenPricingConfig.from_dict(value)
                else:
                    setattr(self, key, value)
            else:
                self.extra_params[key] = value
        
        # Ensure pricing_config is the correct type after potential update by __setattr__
        if isinstance(self.pricing_config, dict):
            logger.debug(f"LLMConfig.update(): pricing_config was updated to a dict. Converting. Value: {self.pricing_config}")
            self.pricing_config = TokenPricingConfig.from_dict(self.pricing_config)
        elif not isinstance(self.pricing_config, TokenPricingConfig):
             logger.warning(
                f"LLMConfig.update(): pricing_config was updated to an unexpected type: {type(self.pricing_config)}. "
                f"Value: {self.pricing_config}. Resetting to default TokenPricingConfig."
            )
             self.pricing_config = TokenPricingConfig()

