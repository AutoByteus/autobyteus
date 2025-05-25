import pytest
import json
import logging
from autobyteus.llm.utils.llm_config import TokenPricingConfig, LLMConfig

# Tests for TokenPricingConfig

def test_token_pricing_config_initialization_defaults():
    """Test TokenPricingConfig initializes with default values."""
    config = TokenPricingConfig()
    assert config.input_token_pricing == 0.0
    assert config.output_token_pricing == 0.0

def test_token_pricing_config_initialization_custom_values():
    """Test TokenPricingConfig with custom pricing values."""
    config = TokenPricingConfig(input_token_pricing=0.001, output_token_pricing=0.002)
    assert config.input_token_pricing == 0.001
    assert config.output_token_pricing == 0.002

def test_token_pricing_config_to_dict():
    """Test TokenPricingConfig to_dict method."""
    config = TokenPricingConfig(input_token_pricing=0.0015, output_token_pricing=0.0025)
    expected_dict = {
        'input_token_pricing': 0.0015,
        'output_token_pricing': 0.0025
    }
    assert config.to_dict() == expected_dict

def test_token_pricing_config_from_dict_full():
    """Test TokenPricingConfig from_dict with all fields."""
    data = {'input_token_pricing': 0.003, 'output_token_pricing': 0.004}
    config = TokenPricingConfig.from_dict(data)
    assert config.input_token_pricing == 0.003
    assert config.output_token_pricing == 0.004

def test_token_pricing_config_from_dict_partial():
    """Test TokenPricingConfig from_dict with missing fields (should default to 0.0)."""
    data_input_only = {'input_token_pricing': 0.005}
    config_input_only = TokenPricingConfig.from_dict(data_input_only)
    assert config_input_only.input_token_pricing == 0.005
    assert config_input_only.output_token_pricing == 0.0  # Default

    data_output_only = {'output_token_pricing': 0.006}
    config_output_only = TokenPricingConfig.from_dict(data_output_only)
    assert config_output_only.input_token_pricing == 0.0 # Default
    assert config_output_only.output_token_pricing == 0.006

def test_token_pricing_config_merge_with_none():
    """Test merge_with None does not change the config."""
    config = TokenPricingConfig(input_token_pricing=0.1, output_token_pricing=0.2)
    config_dict_before = config.to_dict()
    config.merge_with(None)
    assert config.to_dict() == config_dict_before

def test_token_pricing_config_merge_with_another_config():
    """Test merge_with another TokenPricingConfig."""
    base_config = TokenPricingConfig(input_token_pricing=0.1, output_token_pricing=0.2)
    # output_token_pricing will be default 0.0 from override_config as it's not specified there
    override_config = TokenPricingConfig(input_token_pricing=0.15) 
    
    base_config.merge_with(override_config)
    # Override values take precedence, even if they are default for the override object itself.
    assert base_config.input_token_pricing == 0.15 
    assert base_config.output_token_pricing == 0.0 # Overridden by override_config's default output_token_pricing

    base_config_2 = TokenPricingConfig(input_token_pricing=0.3, output_token_pricing=0.4)
    # input_token_pricing will be default 0.0 from override_config_2
    override_config_2 = TokenPricingConfig(output_token_pricing=0.45)
    base_config_2.merge_with(override_config_2)
    assert base_config_2.input_token_pricing == 0.0 
    assert base_config_2.output_token_pricing == 0.45

# Tests for LLMConfig

def test_llm_config_initialization_defaults():
    """Test LLMConfig initializes with default values."""
    config = LLMConfig()
    assert config.rate_limit is None
    assert config.token_limit is None
    assert config.system_message == "You are a helpful assistant."
    assert config.temperature == 0.7
    assert config.max_tokens is None
    assert config.top_p is None
    assert config.frequency_penalty is None
    assert config.presence_penalty is None
    assert config.stop_sequences is None
    assert config.extra_params == {}
    assert isinstance(config.pricing_config, TokenPricingConfig)
    assert config.pricing_config.input_token_pricing == 0.0
    assert config.pricing_config.output_token_pricing == 0.0

def test_llm_config_initialization_custom_values():
    """Test LLMConfig with various custom values."""
    custom_pricing = TokenPricingConfig(0.01, 0.02)
    config = LLMConfig(
        rate_limit=100,
        system_message="Be concise.",
        temperature=0.5,
        max_tokens=1024,
        stop_sequences=["\nUser:"],
        extra_params={"custom_key": "custom_value"},
        pricing_config=custom_pricing
    )
    assert config.rate_limit == 100
    assert config.system_message == "Be concise."
    assert config.temperature == 0.5
    assert config.max_tokens == 1024
    assert config.stop_sequences == ["\nUser:"]
    assert config.extra_params == {"custom_key": "custom_value"}
    assert config.pricing_config == custom_pricing

def test_llm_config_initialization_pricing_config_as_dict(caplog):
    """Test LLMConfig initialization when pricing_config is a dict."""
    with caplog.at_level(logging.DEBUG):
        config = LLMConfig(pricing_config={'input_token_pricing': 0.03, 'output_token_pricing': 0.04}) # type: ignore
    assert isinstance(config.pricing_config, TokenPricingConfig)
    assert config.pricing_config.input_token_pricing == 0.03
    assert config.pricing_config.output_token_pricing == 0.04
    assert "LLMConfig __post_init__: pricing_config is a dict, converting." in caplog.text

def test_llm_config_initialization_pricing_config_invalid_type(caplog):
    """Test LLMConfig initialization with invalid pricing_config type."""
    with caplog.at_level(logging.WARNING):
        config = LLMConfig(pricing_config="invalid_type") # type: ignore
    assert isinstance(config.pricing_config, TokenPricingConfig)
    assert config.pricing_config.input_token_pricing == 0.0 # Should reset to default
    assert config.pricing_config.output_token_pricing == 0.0
    assert "pricing_config was initialized with an unexpected type" in caplog.text
    assert "Resetting to default TokenPricingConfig" in caplog.text

def test_llm_config_default_config_method():
    """Test the LLMConfig.default_config() class method."""
    default_cfg = LLMConfig.default_config()
    assert default_cfg == LLMConfig() # Should be equal to a default-initialized instance

def test_llm_config_to_dict_full_and_excludes_none():
    """Test to_dict method, ensuring None fields are excluded and others are present."""
    custom_pricing_dict = {'input_token_pricing': 0.01, 'output_token_pricing': 0.02}
    config = LLMConfig(
        system_message="Test prompt",
        temperature=0.9,
        max_tokens=500, # A non-None value
        extra_params={"test": 1},
        pricing_config=TokenPricingConfig.from_dict(custom_pricing_dict)
    )
    
    expected_dict = {
        "system_message": "Test prompt",
        "temperature": 0.9,
        "max_tokens": 500,
        "extra_params": {"test": 1},
        "pricing_config": custom_pricing_dict
    }
    assert config.to_dict() == expected_dict
    assert "rate_limit" not in config.to_dict() # Example of a None field excluded

def test_llm_config_to_json():
    """Test to_json method."""
    config = LLMConfig(system_message="JSON Test", temperature=0.6)
    config_dict = config.to_dict()
    json_str = config.to_json()
    assert json.loads(json_str) == config_dict

def test_llm_config_from_dict_full():
    """Test LLMConfig.from_dict with full data."""
    data = {
        "rate_limit": 50,
        "token_limit": 4000,
        "system_message": "Full dict test",
        "temperature": 0.2,
        "max_tokens": 200,
        "top_p": 0.9,
        "frequency_penalty": 0.1,
        "presence_penalty": 0.2,
        "stop_sequences": ["stop"],
        "extra_params": {"extra": "param"},
        "pricing_config": {'input_token_pricing': 0.07, 'output_token_pricing': 0.08}
    }
    config = LLMConfig.from_dict(data)
    assert config.rate_limit == 50
    assert config.system_message == "Full dict test"
    assert config.temperature == 0.2
    assert config.max_tokens == 200
    assert config.extra_params == {"extra": "param"}
    assert isinstance(config.pricing_config, TokenPricingConfig)
    assert config.pricing_config.input_token_pricing == 0.07

def test_llm_config_from_dict_partial():
    """Test LLMConfig.from_dict with partial data (missing fields get defaults)."""
    data = {"system_message": "Partial dict test", "max_tokens": 150}
    config = LLMConfig.from_dict(data)
    assert config.system_message == "Partial dict test"
    assert config.max_tokens == 150
    assert config.temperature == 0.7 # Default
    assert isinstance(config.pricing_config, TokenPricingConfig) # Default

def test_llm_config_from_json_method():
    """Test LLMConfig.from_json method."""
    json_data_str = json.dumps({
        "system_message": "From JSON",
        "temperature": 0.3,
        "pricing_config": {"input_token_pricing": 0.0001, "output_token_pricing": 0.0002}
    })
    config = LLMConfig.from_json(json_data_str)
    assert config.system_message == "From JSON"
    assert config.temperature == 0.3
    assert config.pricing_config.input_token_pricing == 0.0001

def test_llm_config_update_existing_attributes():
    """Test LLMConfig.update() for existing attributes."""
    config = LLMConfig()
    config.update(temperature=0.3, system_message="Updated prompt")
    assert config.temperature == 0.3
    assert config.system_message == "Updated prompt"

def test_llm_config_update_extra_params():
    """Test LLMConfig.update() for adding to extra_params."""
    config = LLMConfig(extra_params={"initial": "value"})
    config.update(new_extra="new_value", another_extra=123)
    assert config.extra_params == {"initial": "value", "new_extra": "new_value", "another_extra": 123}

def test_llm_config_update_pricing_config_with_dict():
    """Test LLMConfig.update() for pricing_config using a dictionary."""
    config = LLMConfig() # Default pricing_config (0.0, 0.0)
    config.update(pricing_config={'input_token_pricing': 0.11, 'output_token_pricing': 0.22})
    assert isinstance(config.pricing_config, TokenPricingConfig)
    assert config.pricing_config.input_token_pricing == 0.11
    assert config.pricing_config.output_token_pricing == 0.22

def test_llm_config_merge_with_none():
    """Test LLMConfig.merge_with(None) does not change the config."""
    original_config = LLMConfig(temperature=0.8)
    config_copy = LLMConfig.from_dict(original_config.to_dict()) # Create a copy
    config_copy.merge_with(None)
    assert config_copy.to_dict() == original_config.to_dict()

def test_llm_config_merge_with_another_config_partial():
    """
    Test LLMConfig.merge_with() another LLMConfig with partial overrides.
    Ensures non-None default values in override_config are applied.
    """
    base = LLMConfig(system_message="Base prompt", temperature=0.7, max_tokens=100)
    # override.system_message will be "You are a helpful assistant." (default for LLMConfig)
    # override.temperature will be 0.5
    # override.max_tokens will be None (default for LLMConfig)
    # override.stop_sequences will be ["\n"]
    override = LLMConfig(temperature=0.5, stop_sequences=["\n"]) 
    
    base.merge_with(override)
    
    # system_message in 'override' is "You are a helpful assistant.", which is not None.
    # So, it overwrites "Base prompt".
    assert base.system_message == "You are a helpful assistant."
    assert base.temperature == 0.5 # Overridden
    # max_tokens in 'override' is None, so it does not overwrite the base value.
    assert base.max_tokens == 100 
    assert base.stop_sequences == ["\n"] # Added

def test_llm_config_merge_with_extra_params_merging():
    """Test that extra_params dictionaries are merged."""
    base = LLMConfig(extra_params={"base_param": 1, "common_param": "base_val"})
    override = LLMConfig(extra_params={"override_param": 2, "common_param": "override_val"})
    
    base.merge_with(override)
    assert base.extra_params == {
        "base_param": 1,
        "common_param": "override_val", # Overridden
        "override_param": 2 # Added
    }

def test_llm_config_merge_with_pricing_config_merging():
    """Test that pricing_config objects are merged."""
    base_pricing = TokenPricingConfig(input_token_pricing=0.1, output_token_pricing=0.2)
    base = LLMConfig(pricing_config=base_pricing)
    
    # override_pricing.input_token_pricing will be 0.0 (default for TokenPricingConfig)
    override_pricing = TokenPricingConfig(output_token_pricing=0.25) 
    override = LLMConfig(pricing_config=override_pricing)
    
    base.merge_with(override)
    # override_pricing.input_token_pricing (0.0) overwrites base_pricing.input_token_pricing (0.1)
    assert base.pricing_config.input_token_pricing == 0.0
    assert base.pricing_config.output_token_pricing == 0.25

def test_llm_config_merge_with_field_set_to_none_in_override_does_not_clear_base():
    """
    Test that if an override_config field has its default None value,
    it does not clear a non-None value in the base config.
    """
    base = LLMConfig(max_tokens=1024, temperature=0.7, system_message="Explicit Base System Message")
    
    # In 'override', max_tokens is None by default.
    # 'temperature' is 0.5 (non-None).
    # 'system_message' is "You are a helpful assistant." (non-None default).
    override = LLMConfig(temperature=0.5) 
    
    base.merge_with(override)
    
    # max_tokens should remain unchanged because override.max_tokens is None.
    assert base.max_tokens == 1024 
    # temperature should be updated as override.temperature (0.5) is not None.
    assert base.temperature == 0.5
    # system_message should be updated as override.system_message ("You are a helpful assistant.") is not None.
    assert base.system_message == "You are a helpful assistant."

