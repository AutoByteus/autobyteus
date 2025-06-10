import pytest
import logging
from typing import Dict, TYPE_CHECKING

from autobyteus.agent.system_prompt_processor.processor_meta import SystemPromptProcessorMeta
from autobyteus.agent.system_prompt_processor.base_processor import BaseSystemPromptProcessor
from autobyteus.agent.system_prompt_processor.processor_registry import default_system_prompt_processor_registry

if TYPE_CHECKING:
    from autobyteus.tools.base_tool import BaseTool
    from autobyteus.agent.context import AgentContext

# Fixture to clear the registry before and after each test in this module
@pytest.fixture(autouse=True)
def clear_default_registry_fixture():
    original_definitions = default_system_prompt_processor_registry.get_all_definitions().copy()
    default_system_prompt_processor_registry.clear()
    yield
    default_system_prompt_processor_registry.clear()
    for name, definition in original_definitions.items():
        default_system_prompt_processor_registry.register_processor(definition)

def test_meta_auto_registers_processor():
    """Test that a processor class using SystemPromptProcessorMeta is auto-registered."""
    
    class MyAutoRegisteredProcessor(BaseSystemPromptProcessor, metaclass=SystemPromptProcessorMeta):
        def get_name(self) -> str:
            return "AutoRegisteredProc"
        def process(self, system_prompt: str, tool_instances: Dict[str, 'BaseTool'], agent_id: str, context: 'AgentContext') -> str:
            return system_prompt # pragma: no cover

    definition = default_system_prompt_processor_registry.get_processor_definition("AutoRegisteredProc")
    assert definition is not None
    assert definition.name == "AutoRegisteredProc"
    assert definition.processor_class == MyAutoRegisteredProcessor

def test_meta_skips_base_class_registration():
    """Test that BaseSystemPromptProcessor itself is not registered."""
    class_name = 'BaseSystemPromptProcessor'
    
    # Define a local class to avoid side-effects on the actual base class
    class BaseSystemPromptProcessor(metaclass=SystemPromptProcessorMeta):
        __abstractmethods__ = frozenset(['process'])
        def get_name(self) -> str: return class_name
        def process(self, system_prompt: str, tool_instances: Dict[str, 'BaseTool'], agent_id: str, context: 'AgentContext') -> str: raise NotImplementedError

    definition = default_system_prompt_processor_registry.get_processor_definition(class_name)
    assert definition is None, f"{class_name} (or abstract class) should not be registered."


def test_meta_skips_abstract_subclass_registration():
    """Test that an abstract subclass is not registered."""
    class AbstractSubProcessor(BaseSystemPromptProcessor, metaclass=SystemPromptProcessorMeta):
        def get_name(self) -> str:
            return "AbstractSubProc"
        # Missing: def process(...)

    definition = default_system_prompt_processor_registry.get_processor_definition("AbstractSubProc")
    assert definition is None

def test_meta_handles_missing_get_name(caplog):
    """Test registration failure if get_name is missing."""
    with caplog.at_level(logging.ERROR):
        class ProcessorMissingGetName(BaseSystemPromptProcessor, metaclass=SystemPromptProcessorMeta):
            def process(self, system_prompt: str, tool_instances: Dict[str, 'BaseTool'], agent_id: str, context: 'AgentContext') -> str:
                return system_prompt # pragma: no cover
    
    assert "is missing required static/class method 'get_name'" in caplog.text
    assert default_system_prompt_processor_registry.get_processor_definition("ProcessorMissingGetName") is None


def test_meta_handles_invalid_get_name_return(caplog):
    """Test registration failure if get_name returns non-string or empty string."""
    with caplog.at_level(logging.ERROR):
        class ProcessorInvalidGetNameReturn(BaseSystemPromptProcessor, metaclass=SystemPromptProcessorMeta):
            def get_name(self): # type: ignore
                return None # Invalid return type
            def process(self, system_prompt: str, tool_instances: Dict[str, 'BaseTool'], agent_id: str, context: 'AgentContext') -> str:
                return system_prompt # pragma: no cover
    
    assert "must return a valid string from static get_name()" in caplog.text
    assert default_system_prompt_processor_registry.get_processor_definition("ProcessorInvalidGetNameReturn") is None
    
    caplog.clear()
    with caplog.at_level(logging.ERROR):
        class ProcessorErrorInGetName(BaseSystemPromptProcessor, metaclass=SystemPromptProcessorMeta):
            def get_name(self) -> str:
                raise RuntimeError("Failure in get_name")
            def process(self, system_prompt: str, tool_instances: Dict[str, 'BaseTool'], agent_id: str, context: 'AgentContext') -> str:
                return system_prompt # pragma: no cover
    
    assert "Failed to auto-register system prompt processor class ProcessorErrorInGetName" in caplog.text
    assert "RuntimeError: Failure in get_name" in caplog.text


def test_meta_registration_with_custom_name():
    """Test auto-registration uses the name from get_name()."""
    class CustomNamedProcessor(BaseSystemPromptProcessor, metaclass=SystemPromptProcessorMeta):
        def get_name(self) -> str:
            return "MyUniqueProcessorName"
        def process(self, system_prompt: str, tool_instances: Dict[str, 'BaseTool'], agent_id: str, context: 'AgentContext') -> str:
            return system_prompt # pragma: no cover

    definition = default_system_prompt_processor_registry.get_processor_definition("MyUniqueProcessorName")
    assert definition is not None
    assert definition.processor_class == CustomNamedProcessor
    assert default_system_prompt_processor_registry.get_processor_definition("CustomNamedProcessor") is None
