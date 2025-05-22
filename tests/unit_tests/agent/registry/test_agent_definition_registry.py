import pytest
import logging
from unittest.mock import patch

from autobyteus.agent.registry.agent_definition_registry import AgentDefinitionRegistry
from autobyteus.agent.registry.agent_definition import AgentDefinition

# --- Test Fixtures ---

@pytest.fixture
def empty_registry() -> AgentDefinitionRegistry:
    """Returns a new, empty AgentDefinitionRegistry instance."""
    return AgentDefinitionRegistry()

@pytest.fixture
def sample_def1() -> AgentDefinition:
    """Returns a sample AgentDefinition."""
    return AgentDefinition(
        name="TestAgent1",
        role="Worker",
        description="Description for TestAgent1 Worker",
        system_prompt="System prompt for TestAgent1 Worker.",
        tool_names=["tool_a", "tool_b"]
    )

@pytest.fixture
def sample_def2() -> AgentDefinition:
    """Returns another sample AgentDefinition."""
    return AgentDefinition(
        name="TestAgent2",
        role="Analyst",
        description="Description for TestAgent2 Analyst",
        system_prompt="System prompt for TestAgent2 Analyst.",
        tool_names=["tool_c"]
    )

@pytest.fixture
def sample_def_same_name_diff_role() -> AgentDefinition:
    """Returns an AgentDefinition with the same name as sample_def1 but a different role."""
    return AgentDefinition(
        name="TestAgent1",
        role="Reviewer",
        description="Description for TestAgent1 Reviewer",
        system_prompt="System prompt for TestAgent1 Reviewer.",
        tool_names=["tool_d"]
    )

@pytest.fixture
def sample_def_diff_name_same_role() -> AgentDefinition:
    """Returns an AgentDefinition with a different name but the same role as sample_def1."""
    return AgentDefinition(
        name="OtherAgent",
        role="Worker",
        description="Description for OtherAgent Worker",
        system_prompt="System prompt for OtherAgent Worker.",
        tool_names=["tool_e"]
    )

# --- Test Cases ---

def test_initialization(empty_registry: AgentDefinitionRegistry):
    """Test that the registry initializes correctly."""
    assert not empty_registry._definitions
    assert len(empty_registry) == 0
    assert empty_registry.list_names() == []
    assert empty_registry.list_all() == []

def test_generate_key(empty_registry: AgentDefinitionRegistry):
    """Test the _generate_key method."""
    key = empty_registry._generate_key("MyAgent", "MyRole")
    assert key == f"MyAgent{AgentDefinitionRegistry._KEY_SEPARATOR}MyRole"

    with pytest.raises(ValueError, match="Definition name cannot be empty"):
        empty_registry._generate_key("", "MyRole")
    
    with pytest.raises(ValueError, match="Definition role cannot be empty"):
        empty_registry._generate_key("MyAgent", "")

def test_register_single_definition(empty_registry: AgentDefinitionRegistry, sample_def1: AgentDefinition):
    """Test successful registration of a single new definition."""
    empty_registry.register(sample_def1)
    expected_key = empty_registry._generate_key(sample_def1.name, sample_def1.role)
    
    assert len(empty_registry) == 1
    assert expected_key in empty_registry._definitions
    assert empty_registry._definitions[expected_key] is sample_def1

def test_register_multiple_definitions(empty_registry: AgentDefinitionRegistry, sample_def1: AgentDefinition, sample_def2: AgentDefinition):
    """Test successful registration of multiple distinct definitions."""
    empty_registry.register(sample_def1)
    empty_registry.register(sample_def2)
    
    expected_key1 = empty_registry._generate_key(sample_def1.name, sample_def1.role)
    expected_key2 = empty_registry._generate_key(sample_def2.name, sample_def2.role)

    assert len(empty_registry) == 2
    assert expected_key1 in empty_registry._definitions
    assert expected_key2 in empty_registry._definitions

def test_register_overwrite_definition(empty_registry: AgentDefinitionRegistry, sample_def1: AgentDefinition, caplog):
    """Test that registering a definition with the same composite key overwrites the old one."""
    empty_registry.register(sample_def1)
    
    new_def_same_key = AgentDefinition(
        name=sample_def1.name,
        role=sample_def1.role,
        description="This is an updated description.",
        system_prompt="Updated system prompt.",
        tool_names=["tool_new"]
    )
    
    expected_key = empty_registry._generate_key(sample_def1.name, sample_def1.role)

    with caplog.at_level(logging.WARNING):
        empty_registry.register(new_def_same_key)
    
    assert len(empty_registry) == 1
    assert empty_registry._definitions[expected_key] is new_def_same_key
    assert empty_registry._definitions[expected_key].description == "This is an updated description."
    assert f"Overwriting existing agent definition for key: '{expected_key}'." in caplog.text

def test_register_same_name_different_role(empty_registry: AgentDefinitionRegistry, sample_def1: AgentDefinition, sample_def_same_name_diff_role: AgentDefinition):
    """Test registering definitions with the same name but different roles."""
    empty_registry.register(sample_def1)
    empty_registry.register(sample_def_same_name_diff_role)
    
    assert len(empty_registry) == 2
    key1 = empty_registry._generate_key(sample_def1.name, sample_def1.role)
    key2 = empty_registry._generate_key(sample_def_same_name_diff_role.name, sample_def_same_name_diff_role.role)
    assert key1 != key2
    assert key1 in empty_registry._definitions
    assert key2 in empty_registry._definitions

def test_register_different_name_same_role(empty_registry: AgentDefinitionRegistry, sample_def1: AgentDefinition, sample_def_diff_name_same_role: AgentDefinition):
    """Test registering definitions with different names but the same role."""
    empty_registry.register(sample_def1)
    empty_registry.register(sample_def_diff_name_same_role)
    
    assert len(empty_registry) == 2
    key1 = empty_registry._generate_key(sample_def1.name, sample_def1.role)
    key2 = empty_registry._generate_key(sample_def_diff_name_same_role.name, sample_def_diff_name_same_role.role)
    assert key1 != key2
    assert key1 in empty_registry._definitions
    assert key2 in empty_registry._definitions

def test_get_existing_definition(empty_registry: AgentDefinitionRegistry, sample_def1: AgentDefinition):
    """Test successful retrieval of a registered definition."""
    empty_registry.register(sample_def1)
    retrieved_def = empty_registry.get(sample_def1.name, sample_def1.role)
    assert retrieved_def is sample_def1

def test_get_non_existing_definition(empty_registry: AgentDefinitionRegistry):
    """Test retrieval of a non-existing definition returns None."""
    retrieved_def = empty_registry.get("NonExistent", "SomeRole")
    assert retrieved_def is None

def test_get_with_invalid_args(empty_registry: AgentDefinitionRegistry, caplog):
    """Test get() with invalid arguments."""
    with caplog.at_level(logging.WARNING):
        assert empty_registry.get("", "ValidRole") is None
        assert "Attempted to retrieve definition with invalid or empty name." in caplog.text
        caplog.clear()
        
        assert empty_registry.get("ValidName", "") is None
        assert "Attempted to retrieve definition with invalid or empty role." in caplog.text
        caplog.clear()

        # Non-string types (pytest might catch this with type hints, but runtime check exists)
        assert empty_registry.get(123, "ValidRole") is None # type: ignore
        assert "Attempted to retrieve definition with invalid or empty name." in caplog.text # Due to isinstance check
        caplog.clear()
        
        assert empty_registry.get("ValidName", True) is None # type: ignore
        assert "Attempted to retrieve definition with invalid or empty role." in caplog.text # Due to isinstance check

def test_unregister_existing_definition(empty_registry: AgentDefinitionRegistry, sample_def1: AgentDefinition):
    """Test successful unregistration of an existing definition."""
    empty_registry.register(sample_def1)
    assert len(empty_registry) == 1
    
    result = empty_registry.unregister(sample_def1.name, sample_def1.role)
    assert result is True
    assert len(empty_registry) == 0
    assert empty_registry.get(sample_def1.name, sample_def1.role) is None

def test_unregister_non_existing_definition(empty_registry: AgentDefinitionRegistry, caplog):
    """Test unregistration of a non-existing definition returns False."""
    with caplog.at_level(logging.WARNING):
        result = empty_registry.unregister("NonExistent", "SomeRole")
    assert result is False
    assert f"AgentDefinition with key 'NonExistent{AgentDefinitionRegistry._KEY_SEPARATOR}SomeRole' (name: 'NonExistent', role: 'SomeRole') not found for unregistration." in caplog.text

def test_unregister_with_invalid_args(empty_registry: AgentDefinitionRegistry, caplog):
    """Test unregister() with invalid arguments."""
    with caplog.at_level(logging.WARNING):
        assert empty_registry.unregister("", "ValidRole") is False
        assert "Attempted to unregister definition with invalid or empty name." in caplog.text
        caplog.clear()

        assert empty_registry.unregister("ValidName", "") is False
        assert "Attempted to unregister definition with invalid or empty role." in caplog.text
        caplog.clear()
        
        assert empty_registry.unregister(None, "ValidRole") is False # type: ignore
        assert "Attempted to unregister definition with invalid or empty name." in caplog.text # isinstance check
        caplog.clear()

def test_contains_check(empty_registry: AgentDefinitionRegistry, sample_def1: AgentDefinition):
    """Test the __contains__ method with various inputs."""
    empty_registry.register(sample_def1)
    key_def1 = empty_registry._generate_key(sample_def1.name, sample_def1.role)

    # Check with AgentDefinition object
    assert sample_def1 in empty_registry
    non_existing_def = AgentDefinition("Ghost", "Phantom", "d", "p", [])
    assert non_existing_def not in empty_registry

    # Check with (name, role) tuple
    assert (sample_def1.name, sample_def1.role) in empty_registry
    assert ("Ghost", "Phantom") not in empty_registry
    assert ("TestAgent1", "NonExistentRole") not in empty_registry # Correct name, wrong role
    assert ("", "Worker") not in empty_registry # Empty name in tuple
    assert ("TestAgent1", "") not in empty_registry # Empty role in tuple


    # Check with composite key string
    assert key_def1 in empty_registry
    assert f"Ghost{AgentDefinitionRegistry._KEY_SEPARATOR}Phantom" not in empty_registry

    # Check with invalid types
    assert 123 not in empty_registry
    assert ["list"] not in empty_registry # type: ignore
    assert ("OnlyName",) not in empty_registry # type: ignore Tuple too short
    assert (123, "RoleString") not in empty_registry # type: ignore Tuple with int

def test_list_names(empty_registry: AgentDefinitionRegistry, sample_def1: AgentDefinition, sample_def2: AgentDefinition):
    """Test list_names() method."""
    assert empty_registry.list_names() == []
    
    empty_registry.register(sample_def1)
    empty_registry.register(sample_def2)
    
    expected_key1 = empty_registry._generate_key(sample_def1.name, sample_def1.role)
    expected_key2 = empty_registry._generate_key(sample_def2.name, sample_def2.role)
    
    names_list = empty_registry.list_names()
    assert len(names_list) == 2
    assert expected_key1 in names_list
    assert expected_key2 in names_list

def test_list_all(empty_registry: AgentDefinitionRegistry, sample_def1: AgentDefinition, sample_def2: AgentDefinition):
    """Test list_all() method."""
    assert empty_registry.list_all() == []
    
    empty_registry.register(sample_def1)
    empty_registry.register(sample_def2)
    
    all_defs = empty_registry.list_all()
    assert len(all_defs) == 2
    assert sample_def1 in all_defs
    assert sample_def2 in all_defs

def test_clear_registry(empty_registry: AgentDefinitionRegistry, sample_def1: AgentDefinition, sample_def2: AgentDefinition):
    """Test clear() method."""
    empty_registry.register(sample_def1)
    empty_registry.register(sample_def2)
    assert len(empty_registry) == 2
    
    empty_registry.clear()
    assert len(empty_registry) == 0
    assert not empty_registry._definitions
    assert empty_registry.list_names() == []

def test_len_registry(empty_registry: AgentDefinitionRegistry, sample_def1: AgentDefinition):
    """Test __len__() method."""
    assert len(empty_registry) == 0
    empty_registry.register(sample_def1)
    assert len(empty_registry) == 1
    empty_registry.unregister(sample_def1.name, sample_def1.role)
    assert len(empty_registry) == 0

def test_get_all(empty_registry: AgentDefinitionRegistry, sample_def1: AgentDefinition):
    """Test get_all() method returns a copy of the definitions."""
    empty_registry.register(sample_def1)
    expected_key = empty_registry._generate_key(sample_def1.name, sample_def1.role)

    all_defs_dict = empty_registry.get_all()
    assert len(all_defs_dict) == 1
    assert expected_key in all_defs_dict
    assert all_defs_dict[expected_key] is sample_def1
    
    # Modify the returned dictionary and check if the original is unaffected
    all_defs_dict.pop(expected_key)
    assert expected_key in empty_registry._definitions, "get_all() should return a copy."
