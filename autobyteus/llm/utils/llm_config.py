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

    def merge_with(self, override_pricing_config: Optional['TokenPricingConfig']) -> None:
        """
        Merges fields from an override TokenPricingConfig object into this one.
        Only non-None fields from the override object are applied.
        Modifies this instance in-place.
        """
        if override_pricing_config is None:
            return

        for f_info in fields(override_pricing_config):
            override_value = getattr(override_pricing_config, f_info.name)
            # For TokenPricingConfig, fields are floats, not optional, so direct assignment is fine.
            # If they were Optional[float], a `if override_value is not None:` check would be needed.
            # Here, any value from override_config takes precedence.
            # Default values (0.0) from an override will replace existing values.
            setattr(self, f_info.name, override_value)
        logger.debug(f"TokenPricingConfig merged. Current state: {self.to_dict()}")


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
    uses_max_completion_tokens: bool = False
    extra_params: Dict[str, Any] = field(default_factory=dict)
    pricing_config: TokenPricingConfig = field(default_factory=TokenPricingConfig)

    def __post_init__(self):
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
        data = {}
        for f in fields(self):
            field_value = getattr(self, f.name)
            if f.name == 'pricing_config':
                if isinstance(self.pricing_config, TokenPricingConfig):
                    data[f.name] = self.pricing_config.to_dict()
                elif isinstance(self.pricing_config, dict): 
                    data[f.name] = self.pricing_config 
                else: 
                    logger.error(f"LLMConfig.to_dict(): pricing_config has unexpected type {type(self.pricing_config)} after checks.")
                    data[f.name] = {} 
            else:
                data[f.name] = field_value
        
        return {k: v for k, v in data.items() if v is not None}


    def to_json(self) -> str:
        return json.dumps(self.to_dict())

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'LLMConfig':
        data_copy = data.copy()
        pricing_config_data = data_copy.pop('pricing_config', {})
        
        # Create a new dictionary for known fields to avoid passing them in twice
        known_fields = {
            'rate_limit', 'token_limit', 'system_message', 'temperature', 
            'max_tokens', 'top_p', 'frequency_penalty', 'presence_penalty', 
            'stop_sequences', 'uses_max_completion_tokens', 'extra_params', 
            'pricing_config'
        }
        
        init_kwargs = {k: v for k, v in data_copy.items() if k in known_fields}
        
        config = cls(
            rate_limit=init_kwargs.get('rate_limit'),
            token_limit=init_kwargs.get('token_limit'),
            system_message=init_kwargs.get('system_message', "You are a helpful assistant."),
            temperature=init_kwargs.get('temperature', 0.7),
            max_tokens=init_kwargs.get('max_tokens'),
            top_p=init_kwargs.get('top_p'),
            frequency_penalty=init_kwargs.get('frequency_penalty'),
            presence_penalty=init_kwargs.get('presence_penalty'),
            stop_sequences=init_kwargs.get('stop_sequences'),
            uses_max_completion_tokens=init_kwargs.get('uses_max_completion_tokens', False),
            extra_params=init_kwargs.get('extra_params', {}),
            pricing_config=pricing_config_data 
        )
        return config

    @classmethod
    def from_json(cls, json_str: str) -> 'LLMConfig':
        data = json.loads(json_str)
        return cls.from_dict(data)

    def update(self, **kwargs):
        """Update config with new values from a dictionary."""
        for key, value in kwargs.items():
            if hasattr(self, key):
                if key == 'pricing_config' and isinstance(value, dict):
                    if self.pricing_config:
                        self.pricing_config.merge_with(TokenPricingConfig.from_dict(value))
                    else: # Should not happen due to default_factory
                        self.pricing_config = TokenPricingConfig.from_dict(value)
                else:
                    setattr(self, key, value)
            else:
                self.extra_params[key] = value
        
        if isinstance(self.pricing_config, dict): # Should be handled by __post_init__ or above
            logger.debug(f"LLMConfig.update(): pricing_config was updated to a dict. Converting. Value: {self.pricing_config}")
            self.pricing_config = TokenPricingConfig.from_dict(self.pricing_config)
        elif not isinstance(self.pricing_config, TokenPricingConfig): # Should not happen
             logger.warning(
                f"LLMConfig.update(): pricing_config was updated to an unexpected type: {type(self.pricing_config)}. "
                f"Value: {self.pricing_config}. Resetting to default TokenPricingConfig."
            )
             self.pricing_config = TokenPricingConfig()
        logger.debug(f"LLMConfig updated via kwargs. Current system_message: '{self.system_message}', temperature: {self.temperature}")

    def merge_with(self, override_config: Optional['LLMConfig']) -> None:
        """
        Merges fields from an override LLMConfig object into this one.
        Only non-None fields from the override_config are applied.
        Modifies this instance in-place.
        """
        if override_config is None:
            return

        logger.debug(f"Merging LLMConfig. Base (self) before merge: rate_limit={self.rate_limit}, temp={self.temperature}")
        logger.debug(f"Override config provided: rate_limit={override_config.rate_limit}, temp={override_config.temperature}")

        for f_info in fields(override_config):
            override_value = getattr(override_config, f_info.name)
            
            # Special handling for booleans where we want to merge if it's not the default
            # For `uses_max_completion_tokens`, the default is False, so `if override_value:` is fine
            is_boolean_field = f_info.type == bool
            
            # Standard check for None, but also merge if it's a non-default boolean
            if override_value is not None:
                # For uses_max_completion_tokens, `False` is a valid override value, but `None` is not
                if is_boolean_field and override_value is False and getattr(self, f_info.name) is True:
                     setattr(self, f_info.name, override_value)
                elif f_info.name == 'pricing_config':
                    if not isinstance(self.pricing_config, TokenPricingConfig):
                        self.pricing_config = TokenPricingConfig()
                    
                    if isinstance(override_value, TokenPricingConfig):
                         self.pricing_config.merge_with(override_value)
                    elif isinstance(override_value, dict):
                        self.pricing_config.merge_with(TokenPricingConfig.from_dict(override_value))
                    else:
                        logger.warning(f"Skipping merge for pricing_config due to unexpected override type: {type(override_value)}")
                elif f_info.name == 'extra_params':
                    if isinstance(override_value, dict) and isinstance(self.extra_params, dict):
                        self.extra_params.update(override_value)
                    else:
                        setattr(self, f_info.name, override_value)
                else:
                    setattr(self, f_info.name, override_value)
        logger.debug(f"LLMConfig merged. Current state after merge: rate_limit={self.rate_limit}, temp={self.temperature}, system_message='{self.system_message}'")
