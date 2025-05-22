# File: tests/unit_tests/tools/test_tool_config.py
import pytest
from autobyteus.tools.tool_config import ToolConfig

def test_tool_config_creation_empty():
    config = ToolConfig()
    assert config.params == {}
    assert len(config) == 0
    assert not config

def test_tool_config_creation_with_params():
    params = {'param1': 'value1', 'param2': 42}
    config = ToolConfig(params=params)
    assert config.params == params
    assert len(config) == 2
    assert config

def test_tool_config_invalid_params():
    with pytest.raises(TypeError, match="params must be a dictionary"):
        ToolConfig(params="not_a_dict")

def test_to_dict():
    params = {'param1': 'value1', 'param2': 42}
    config = ToolConfig(params=params)
    result = config.to_dict()
    
    assert result == params
    assert result is not config.params  # Should be a copy

def test_from_dict():
    data = {'param1': 'value1', 'param2': 42}
    config = ToolConfig.from_dict(data)
    
    assert config.params == data
    assert config.params is not data  # Should be a copy

def test_from_dict_invalid():
    with pytest.raises(TypeError, match="config_data must be a dictionary"):
        ToolConfig.from_dict("not_a_dict")

def test_merge():
    config1 = ToolConfig(params={'param1': 'value1', 'param2': 'value2'})
    config2 = ToolConfig(params={'param2': 'new_value2', 'param3': 'value3'})
    
    merged = config1.merge(config2)
    
    expected = {'param1': 'value1', 'param2': 'new_value2', 'param3': 'value3'}
    assert merged.params == expected
    
    # Original configs should be unchanged
    assert config1.params == {'param1': 'value1', 'param2': 'value2'}
    assert config2.params == {'param2': 'new_value2', 'param3': 'value3'}

def test_merge_invalid():
    config = ToolConfig()
    with pytest.raises(TypeError, match="Can only merge with another ToolConfig instance"):
        config.merge("not_a_config")

def test_get_constructor_kwargs():
    params = {'param1': 'value1', 'param2': 42}
    config = ToolConfig(params=params)
    kwargs = config.get_constructor_kwargs()
    
    assert kwargs == params
    assert kwargs is not config.params  # Should be a copy

def test_get():
    config = ToolConfig(params={'param1': 'value1', 'param2': 42})
    
    assert config.get('param1') == 'value1'
    assert config.get('param2') == 42
    assert config.get('nonexistent') is None
    assert config.get('nonexistent', 'default') == 'default'

def test_set():
    config = ToolConfig()
    config.set('new_param', 'new_value')
    
    assert config.get('new_param') == 'new_value'
    assert len(config) == 1

def test_update():
    config = ToolConfig(params={'param1': 'value1'})
    new_params = {'param1': 'updated_value1', 'param2': 'value2'}
    
    config.update(new_params)
    
    assert config.get('param1') == 'updated_value1'
    assert config.get('param2') == 'value2'
    assert len(config) == 2

def test_update_invalid():
    config = ToolConfig()
    with pytest.raises(TypeError, match="params must be a dictionary"):
        config.update("not_a_dict")

def test_repr():
    params = {'param1': 'value1', 'param2': 42}
    config = ToolConfig(params=params)
    
    expected = f"ToolConfig(params={params})"
    assert repr(config) == expected
