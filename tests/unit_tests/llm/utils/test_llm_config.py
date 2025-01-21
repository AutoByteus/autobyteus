import pytest
from autobyteus.llm.utils.llm_config import LLMConfig, TokenPricingConfig

@pytest.fixture
def pricing_config():
    return TokenPricingConfig(
        input_token_pricing=0.5,
        output_token_pricing=1.0
    )

@pytest.fixture
def llm_config(pricing_config):
    return LLMConfig(
        rate_limit=40,
        token_limit=8192,
        system_message="Test message",
        temperature=0.8,
        max_tokens=100,
        top_p=0.9,
        frequency_penalty=0.1,
        presence_penalty=0.2,
        stop_sequences=["stop"],
        extra_params={"param1": "value1"},
        pricing_config=pricing_config
    )

# TokenPricingConfig Tests
def test_token_pricing_config_default_values():
    config = TokenPricingConfig()
    assert config.input_token_pricing == 0.0
    assert config.output_token_pricing == 0.0

def test_token_pricing_config_to_dict(pricing_config):
    expected_dict = {
        'input_token_pricing': 0.5,
        'output_token_pricing': 1.0
    }
    assert pricing_config.to_dict() == expected_dict

def test_token_pricing_config_from_dict():
    data = {
        'input_token_pricing': 0.5,
        'output_token_pricing': 1.0
    }
    config = TokenPricingConfig.from_dict(data)
    assert config.input_token_pricing == 0.5
    assert config.output_token_pricing == 1.0

def test_token_pricing_config_from_empty_dict():
    config = TokenPricingConfig.from_dict({})
    assert config.input_token_pricing == 0.0
    assert config.output_token_pricing == 0.0

# LLMConfig Tests
def test_llm_config_default_values():
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

def test_llm_config_to_dict(llm_config):
    config_dict = llm_config.to_dict()
    assert config_dict['rate_limit'] == 40
    assert config_dict['token_limit'] == 8192
    assert config_dict['system_message'] == "Test message"
    assert config_dict['temperature'] == 0.8
    assert config_dict['max_tokens'] == 100
    assert config_dict['top_p'] == 0.9
    assert config_dict['frequency_penalty'] == 0.1
    assert config_dict['presence_penalty'] == 0.2
    assert config_dict['stop_sequences'] == ["stop"]
    assert config_dict['extra_params'] == {"param1": "value1"}
    assert config_dict['pricing_config']['input_token_pricing'] == 0.5
    assert config_dict['pricing_config']['output_token_pricing'] == 1.0

def test_llm_config_json_serialization(llm_config):
    json_str = llm_config.to_json()
    restored_config = LLMConfig.from_json(json_str)
    
    assert restored_config.rate_limit == llm_config.rate_limit
    assert restored_config.token_limit == llm_config.token_limit
    assert restored_config.system_message == llm_config.system_message
    assert restored_config.temperature == llm_config.temperature
    assert restored_config.max_tokens == llm_config.max_tokens
    assert restored_config.top_p == llm_config.top_p
    assert restored_config.frequency_penalty == llm_config.frequency_penalty
    assert restored_config.presence_penalty == llm_config.presence_penalty
    assert restored_config.stop_sequences == llm_config.stop_sequences
    assert restored_config.extra_params == llm_config.extra_params
    assert restored_config.pricing_config.input_token_pricing == llm_config.pricing_config.input_token_pricing
    assert restored_config.pricing_config.output_token_pricing == llm_config.pricing_config.output_token_pricing

def test_llm_config_from_partial_dict():
    data = {
        'rate_limit': 40,
        'token_limit': 8192
    }
    config = LLMConfig.from_dict(data)
    assert config.rate_limit == 40
    assert config.token_limit == 8192
    assert config.system_message == "You are a helpful assistant."
    assert config.temperature == 0.7
    assert config.max_tokens is None
    assert config.top_p is None
    assert config.frequency_penalty is None
    assert config.presence_penalty is None
    assert config.stop_sequences is None
    assert config.extra_params == {}
    assert isinstance(config.pricing_config, TokenPricingConfig)

def test_llm_config_update(llm_config):
    llm_config.update(
        rate_limit=50,
        token_limit=4096,
        unknown_param="value"
    )
    assert llm_config.rate_limit == 50
    assert llm_config.token_limit == 4096
    assert llm_config.extra_params["unknown_param"] == "value"

def test_llm_config_with_none_values():
    config = LLMConfig(
        rate_limit=None,
        token_limit=None,
        max_tokens=None
    )
    config_dict = config.to_dict()
    assert 'rate_limit' not in config_dict
    assert 'token_limit' not in config_dict
    assert 'max_tokens' not in config_dict

def test_llm_config_with_empty_pricing_config():
    config = LLMConfig()
    config_dict = config.to_dict()
    assert config_dict['pricing_config'] == {'input_token_pricing': 0.0, 'output_token_pricing': 0.0}


def test_token_pricing_config_deserialization_with_extra_fields():
    data = {
        'input_token_pricing': 0.5,
        'output_token_pricing': 1.0,
        'extra_field': 'ignored'
    }
    config = TokenPricingConfig.from_dict(data)
    assert config.input_token_pricing == 0.5
    assert config.output_token_pricing == 1.0
    assert not hasattr(config, 'extra_field')

def test_token_pricing_config_deserialization_with_invalid_types():
    data = {
        'input_token_pricing': '0.5',  # string instead of float
        'output_token_pricing': '1.0'  # string instead of float
    }
    with pytest.raises(TypeError):
        TokenPricingConfig.from_dict(data)

def test_llm_config_deserialization_complete():
    data = {
        'rate_limit': 40,
        'token_limit': 8192,
        'system_message': 'Custom message',
        'temperature': 0.8,
        'max_tokens': 100,
        'top_p': 0.9,
        'frequency_penalty': 0.1,
        'presence_penalty': 0.2,
        'stop_sequences': ['stop1', 'stop2'],
        'extra_params': {'key1': 'value1'},
        'pricing_config': {
            'input_token_pricing': 0.5,
            'output_token_pricing': 1.0
        }
    }
    config = LLMConfig.from_dict(data)
    assert config.rate_limit == 40
    assert config.token_limit == 8192
    assert config.system_message == 'Custom message'
    assert config.temperature == 0.8
    assert config.max_tokens == 100
    assert config.top_p == 0.9
    assert config.frequency_penalty == 0.1
    assert config.presence_penalty == 0.2
    assert config.stop_sequences == ['stop1', 'stop2']
    assert config.extra_params == {'key1': 'value1'}
    assert config.pricing_config.input_token_pricing == 0.5
    assert config.pricing_config.output_token_pricing == 1.0

def test_llm_config_deserialization_invalid_json():
    invalid_json = "{'invalid': json}"
    with pytest.raises(json.JSONDecodeError):
        LLMConfig.from_json(invalid_json)

def test_llm_config_deserialization_missing_pricing_config():
    data = {
        'rate_limit': 40,
        'token_limit': 8192
    }
    config = LLMConfig.from_dict(data)
    assert isinstance(config.pricing_config, TokenPricingConfig)
    assert config.pricing_config.input_token_pricing == 0.0
    assert config.pricing_config.output_token_pricing == 0.0

def test_llm_config_deserialization_invalid_pricing_config():
    data = {
        'rate_limit': 40,
        'pricing_config': 'invalid'  # Should be a dict
    }
    with pytest.raises(AttributeError):
        LLMConfig.from_dict(data)

def test_llm_config_deserialization_with_none_values():
    data = {
        'rate_limit': None,
        'token_limit': None,
        'max_tokens': None,
        'pricing_config': {
            'input_token_pricing': 0.5,
            'output_token_pricing': 1.0
        }
    }
    config = LLMConfig.from_dict(data)
    assert config.rate_limit is None
    assert config.token_limit is None
    assert config.max_tokens is None
    assert config.pricing_config.input_token_pricing == 0.5
    assert config.pricing_config.output_token_pricing == 1.0

def test_llm_config_deserialization_with_extra_fields():
    data = {
        'rate_limit': 40,
        'unknown_field': 'value',
        'pricing_config': {
            'input_token_pricing': 0.5,
            'output_token_pricing': 1.0
        }
    }
    config = LLMConfig.from_dict(data)
    assert config.rate_limit == 40
    assert not hasattr(config, 'unknown_field')
    assert config.pricing_config.input_token_pricing == 0.5
    assert config.pricing_config.output_token_pricing == 1.0

def test_llm_config_deserialization_invalid_types():
    data = {
        'rate_limit': '40',  # string instead of int
        'temperature': '0.7',  # string instead of float
        'pricing_config': {
            'input_token_pricing': 0.5,
            'output_token_pricing': 1.0
        }
    }
    with pytest.raises(TypeError):
        LLMConfig.from_dict(data)