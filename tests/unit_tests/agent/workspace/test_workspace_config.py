# file: autobyteus/tests/unit_tests/agent/workspace/test_workspace_config.py
import pytest
from autobyteus.agent.workspace.workspace_config import WorkspaceConfig

def test_initialization_and_immutability():
    """Tests that the config is immutable after creation."""
    original_params = {"path": "/dev/null", "readonly": True}
    config = WorkspaceConfig(params=original_params)

    # Modify the original dictionary
    original_params["path"] = "/temp"

    # The config instance should remain unchanged because it stores a copy
    assert config.get("path") == "/dev/null"
    assert config.to_dict()["path"] == "/dev/null"

    # to_dict() should also return a copy
    config_dict = config.to_dict()
    config_dict["readonly"] = False
    assert config.get("readonly") is True

def test_set_returns_new_instance():
    """Tests that set() is immutable and returns a new instance."""
    params = {"a": 1, "b": 2}
    c1 = WorkspaceConfig(params)
    c2 = c1.set("c", 3)

    assert c1 is not c2
    assert c1.to_dict() == {"a": 1, "b": 2}  # Original is unchanged
    assert c2.to_dict() == {"a": 1, "b": 2, "c": 3}  # New instance has the change

def test_update_returns_new_instance():
    """Tests that update() is immutable and returns a new instance."""
    params = {"a": 1, "b": 2}
    c1 = WorkspaceConfig(params)
    c2 = c1.update({"b": 99, "d": 100})

    assert c1 is not c2
    assert c1.to_dict() == {"a": 1, "b": 2}  # Original is unchanged
    assert c2.to_dict() == {"a": 1, "b": 99, "d": 100} # New instance has the change

def test_merge_returns_new_instance():
    """Tests that merge() returns a new instance with combined params."""
    c1 = WorkspaceConfig({"a": 1, "b": 2})
    c2 = WorkspaceConfig({"b": 99, "c": 3})
    c3 = c1.merge(c2)

    assert c1.to_dict() == {"a": 1, "b": 2} # Unchanged
    assert c2.to_dict() == {"b": 99, "c": 3} # Unchanged
    assert c3.to_dict() == {"a": 1, "b": 99, "c": 3} # Merged, c2 takes precedence
    assert c3 is not c1 and c3 is not c2

def test_equality():
    """Tests value-based equality, ignoring key order."""
    c1 = WorkspaceConfig({"a": 1, "b": {"c": 3}})
    c2 = WorkspaceConfig({"b": {"c": 3}, "a": 1}) # Same, different order
    c3 = WorkspaceConfig({"a": 1, "b": {"c": 4}}) # Different nested value
    c4 = WorkspaceConfig({"a": 1}) # Different keys

    assert c1 == c2
    assert c1 != c3
    assert c1 != c4
    assert (c1 == "not a config object") is False

def test_hashing_and_dictionary_usage():
    """Tests that configs are hashable and can be used as dict keys."""
    c1 = WorkspaceConfig({"a": 1, "b": 2})
    c2 = WorkspaceConfig({"b": 2, "a": 1}) # Equal to c1
    c3 = WorkspaceConfig({"a": 1, "b": 3}) # Not equal to c1

    assert hash(c1) == hash(c2)
    assert hash(c1) != hash(c3)

    cache = {c1: "instance_for_c1"}
    
    # Check if an equal object can retrieve the value
    assert c2 in cache
    assert cache[c2] == "instance_for_c1"

    # Check that an unequal object is not found
    assert c3 not in cache
    with pytest.raises(KeyError):
        _ = cache[c3]

def test_from_dict_and_to_dict():
    """Tests the from_dict and to_dict methods."""
    params = {"key": "value", "nested": {"num": 123}}
    config = WorkspaceConfig.from_dict(params)

    assert isinstance(config, WorkspaceConfig)
    assert config.to_dict() == params

    # Test that from_dict raises TypeError for non-dict input
    with pytest.raises(TypeError, match="config_data must be a dictionary"):
        WorkspaceConfig.from_dict("not a dict")

def test_get_method():
    """Tests the get() method for retrieving values."""
    config = WorkspaceConfig({"key": "value"})
    assert config.get("key") == "value"
    assert config.get("nonexistent") is None
    assert config.get("nonexistent", "default_val") == "default_val"

def test_special_methods():
    """Tests __len__, __bool__, and __repr__."""
    empty_config = WorkspaceConfig()
    config = WorkspaceConfig({"a": 1})

    # __len__
    assert len(empty_config) == 0
    assert len(config) == 1

    # __bool__
    assert bool(empty_config) is False
    assert bool(config) is True

    # __repr__
    assert repr(config) == "WorkspaceConfig(params={'a': 1})"
    assert repr(empty_config) == "WorkspaceConfig(params={})"

def test_hashing_with_complex_types():
    """Tests that hashing is stable with complex types like sets."""
    # Sets are unordered, so their representation must be sorted for stable hashing
    c1 = WorkspaceConfig({"data": {1, 2, 3}, "name": "c1"})
    c2 = WorkspaceConfig({"name": "c1", "data": {3, 1, 2}}) # Same data
    c3 = WorkspaceConfig({"name": "c1", "data": {1, 2, 4}}) # Different data

    assert c1 == c2
    assert hash(c1) == hash(c2)
    assert c1 != c3
    assert hash(c1) != hash(c3)

def test_type_errors_for_invalid_input():
    """Tests that methods raise TypeError on invalid input types."""
    config = WorkspaceConfig()
    
    with pytest.raises(TypeError, match="Can only merge with another WorkspaceConfig instance"):
        config.merge({"a": 1})

    with pytest.raises(TypeError, match="params must be a mapping"):
        config.update("not a dict")
