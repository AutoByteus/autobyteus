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
            
            if override_value is not None:
                if f_info.name == 'pricing_config':
                    # Ensure self.pricing_config is an object (should be by __post_init__)
                    if not isinstance(self.pricing_config, TokenPricingConfig):
                        self.pricing_config = TokenPricingConfig() # Should not be needed
                    
                    # override_value here is override_config.pricing_config, which is TokenPricingConfig
                    if isinstance(override_value, TokenPricingConfig):
                         self.pricing_config.merge_with(override_value)
                    elif isinstance(override_value, dict): # Should not happen if override_config is LLMConfig
                        self.pricing_config.merge_with(TokenPricingConfig.from_dict(override_value))
                    else:
                        logger.warning(f"Skipping merge for pricing_config due to unexpected override type: {type(override_value)}")
                elif f_info.name == 'extra_params':
                    # For extra_params (dict), merge dictionaries
                    if isinstance(override_value, dict) and isinstance(self.extra_params, dict):
                        self.extra_params.update(override_value)
                    else:
                        setattr(self, f_info.name, override_value) # Fallback to direct set if types mismatch
                else:
                    setattr(self, f_info.name, override_value)
        logger.debug(f"LLMConfig merged. Current state after merge: rate_limit={self.rate_limit}, temp={self.temperature}, system_message='{self.system_message}'")

