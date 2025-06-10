import pytest
from typing import Dict, TYPE_CHECKING

from autobyteus.agent.system_prompt_processor.base_processor import BaseSystemPromptProcessor
from autobyteus.agent.system_prompt_processor.processor_definition import SystemPromptProcessorDefinition
from autobyteus.agent.system_prompt_processor.processor_registry import SystemPromptProcessorRegistry, default_system_prompt_processor_registry

if TYPE_CHECKING:
    from autobyteus.tools.base_tool import BaseTool
    from autobyteus.agent.context import AgentContext

class ProcA(BaseSystemPromptProcessor):
    def get_name(self) -> str: return "ProcA"
    def process(self, system_prompt: str, tool_instances: Dict[str, 'BaseTool'], agent_id: str, context: 'AgentContext') -> str: return system_prompt

class ProcB(BaseSystemPromptProcessor):
    def get_name(self) -> str: return "ProcB"
    def process(self, system_prompt: str, tool_instances: Dict[str, 'BaseTool'], agent_id: str, context: 'AgentContext') -> str: return system_prompt
    
class ProcWithInitError(BaseSystemPromptProcessor):
    def get_name(self) -> str: return "ProcWithInitError"
    def __init__(self): raise ValueError("Init failed")
    def process(self, system_prompt: str, tool_instances: Dict[str, 'BaseTool'], agent_id: str, context: 'AgentContext') -> str: return system_prompt


@pytest.fixture(autouse=True)
def clear_registry_before_each_test():
    """Fixture to ensure the default registry is clean before each test."""
    original_definitions = default_system_prompt_processor_registry.get_all_definitions().copy()
    default_system_prompt_processor_registry.clear()
    yield
    default_system_prompt_processor_registry.clear()
    for name, definition in original_definitions.items():
        default_system_prompt_processor_registry.register_processor(definition)


def test_registry_singleton():
    """Test that default_system_prompt_processor_registry is a singleton."""
    registry1 = default_system_prompt_processor_registry
    registry2 = SystemPromptProcessorRegistry() # Will return the same instance
    assert registry1 is registry2

def test_register_processor_valid():
    """Test registering a valid processor definition."""
    definition_a = SystemPromptProcessorDefinition(name="ProcA", processor_class=ProcA)
    default_system_prompt_processor_registry.register_processor(definition_a)
    assert default_system_prompt_processor_registry.get_processor_definition("ProcA") == definition_a
    assert len(default_system_prompt_processor_registry) == 1

def test_register_processor_overwrite(caplog):
    """Test overwriting an existing processor definition."""
    definition1 = SystemPromptProcessorDefinition(name="ProcOverwrite", processor_class=ProcA)
    definition2 = SystemPromptProcessorDefinition(name="ProcOverwrite", processor_class=ProcB)
    
    default_system_prompt_processor_registry.register_processor(definition1)
    assert default_system_prompt_processor_registry.get_processor_definition("ProcOverwrite") == definition1
    
    default_system_prompt_processor_registry.register_processor(definition2)
    assert "Overwriting existing system prompt processor definition for name: 'ProcOverwrite'." in caplog.text
    assert default_system_prompt_processor_registry.get_processor_definition("ProcOverwrite") == definition2
    assert len(default_system_prompt_processor_registry) == 1

def test_register_processor_invalid_type():
    """Test registering an invalid definition type."""
    with pytest.raises(TypeError, match="Expected SystemPromptProcessorDefinition instance, got InvalidDef."):
        default_system_prompt_processor_registry.register_processor(type("InvalidDef", (), {})()) # type: ignore

def test_get_processor_definition_found_not_found():
    """Test get_processor_definition for existing and non-existing processors."""
    definition_a = SystemPromptProcessorDefinition(name="ProcA", processor_class=ProcA)
    default_system_prompt_processor_registry.register_processor(definition_a)

    assert default_system_prompt_processor_registry.get_processor_definition("ProcA") == definition_a
    assert default_system_prompt_processor_registry.get_processor_definition("NonExistentProc") is None

def test_get_processor_definition_invalid_name(caplog):
    """Test get_processor_definition with invalid name types."""
    assert default_system_prompt_processor_registry.get_processor_definition(None) is None # type: ignore
    assert "Attempted to retrieve system prompt processor definition with non-string name: NoneType." in caplog.text
    caplog.clear()
    assert default_system_prompt_processor_registry.get_processor_definition(123) is None # type: ignore
    assert "Attempted to retrieve system prompt processor definition with non-string name: int." in caplog.text

def test_get_processor_found_and_instantiable():
    """Test get_processor for an existing and instantiable processor."""
    definition_a = SystemPromptProcessorDefinition(name="ProcA", processor_class=ProcA)
    default_system_prompt_processor_registry.register_processor(definition_a)
    
    processor_instance = default_system_prompt_processor_registry.get_processor("ProcA")
    assert isinstance(processor_instance, ProcA)

def test_get_processor_not_found():
    """Test get_processor for a non-existing processor."""
    assert default_system_prompt_processor_registry.get_processor("NonExistentProc") is None

def test_get_processor_instantiation_error(caplog):
    """Test get_processor when the processor class fails to instantiate."""
    definition_err = SystemPromptProcessorDefinition(name="ProcWithInitError", processor_class=ProcWithInitError)
    default_system_prompt_processor_registry.register_processor(definition_err)
    
    processor_instance = default_system_prompt_processor_registry.get_processor("ProcWithInitError")
    assert processor_instance is None
    assert "Failed to instantiate system prompt processor 'ProcWithInitError'" in caplog.text
    assert "ValueError: Init failed" in caplog.text

def test_list_processor_names():
    """Test listing registered processor names."""
    definition_a = SystemPromptProcessorDefinition(name="ProcA", processor_class=ProcA)
    definition_b = SystemPromptProcessorDefinition(name="ProcB", processor_class=ProcB)
    default_system_prompt_processor_registry.register_processor(definition_a)
    default_system_prompt_processor_registry.register_processor(definition_b)

    names = default_system_prompt_processor_registry.list_processor_names()
    assert sorted(names) == sorted(["ProcA", "ProcB"])

def test_get_all_definitions():
    """Test getting all registered definitions."""
    definition_a = SystemPromptProcessorDefinition(name="ProcA", processor_class=ProcA)
    default_system_prompt_processor_registry.register_processor(definition_a)

    all_defs = default_system_prompt_processor_registry.get_all_definitions()
    assert len(all_defs) == 1
    assert all_defs["ProcA"] == definition_a

def test_clear_registry():
    """Test clearing all definitions from the registry."""
    definition_a = SystemPromptProcessorDefinition(name="ProcA", processor_class=ProcA)
    default_system_prompt_processor_registry.register_processor(definition_a)
    assert len(default_system_prompt_processor_registry) == 1
    
    default_system_prompt_processor_registry.clear()
    assert len(default_system_prompt_processor_registry) == 0
    assert default_system_prompt_processor_registry.get_processor_definition("ProcA") is None

def test_registry_len_and_contains():
    """Test __len__ and __contains__ magic methods."""
    assert len(default_system_prompt_processor_registry) == 0
    assert "ProcA" not in default_system_prompt_processor_registry

    definition_a = SystemPromptProcessorDefinition(name="ProcA", processor_class=ProcA)
    default_system_prompt_processor_registry.register_processor(definition_a)

    assert len(default_system_prompt_processor_registry) == 1
    assert "ProcA" in default_system_prompt_processor_registry
    assert "NonExistent" not in default_system_prompt_processor_registry
    assert 123 not in default_system_prompt_processor_registry # Test with invalid type for contains
