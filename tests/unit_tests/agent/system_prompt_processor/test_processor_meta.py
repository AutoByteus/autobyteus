import pytest
import logging
from typing import Dict

from autobyteus.agent.system_prompt_processor.processor_meta import SystemPromptProcessorMeta
from autobyteus.agent.system_prompt_processor.base_processor import BaseSystemPromptProcessor
from autobyteus.agent.system_prompt_processor.processor_registry import default_system_prompt_processor_registry
from autobyteus.tools.base_tool import BaseTool

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
        @classmethod
        def get_name(cls) -> str:
            return "AutoRegisteredProc"
        def process(self, system_prompt: str, tool_instances: Dict[str, 'BaseTool'], agent_id: str) -> str:
            return system_prompt # pragma: no cover

    definition = default_system_prompt_processor_registry.get_processor_definition("AutoRegisteredProc")
    assert definition is not None
    assert definition.name == "AutoRegisteredProc"
    assert definition.processor_class == MyAutoRegisteredProcessor

def test_meta_skips_base_class_registration():
    """Test that BaseSystemPromptProcessor itself is not registered."""
    # BaseSystemPromptProcessor is defined with the metaclass in its own module.
    # We check if it (or any class named 'BaseSystemPromptProcessor') was registered.
    # This relies on the fixture clearing any pre-existing registrations from the source file.
    
    # Define a class with the same name as the base class if the original base is not available or to isolate test
    class BaseSystemPromptProcessor(metaclass=SystemPromptProcessorMeta): # type: ignore
        # This is a local "BaseSystemPromptProcessor" for the test
        __abstractmethods__ = frozenset(['process']) # Make it abstract
        @classmethod
        def get_name(cls) -> str: return "BaseSystemPromptProcessor"
        def process(self, system_prompt: str, tool_instances: Dict[str, 'BaseTool'], agent_id: str) -> str: raise NotImplementedError

    definition = default_system_prompt_processor_registry.get_processor_definition("BaseSystemPromptProcessor")
    assert definition is None, "BaseSystemPromptProcessor (or abstract class) should not be registered."

def test_meta_skips_abstract_subclass_registration():
    """Test that an abstract subclass is not registered."""
    class AbstractSubProcessor(BaseSystemPromptProcessor, metaclass=SystemPromptProcessorMeta):
        # No 'process' method, so it's abstract
        @classmethod
        def get_name(cls) -> str:
            return "AbstractSubProc"
        # Missing: def process(...)

    definition = default_system_prompt_processor_registry.get_processor_definition("AbstractSubProc")
    assert definition is None

def test_meta_handles_missing_get_name(caplog):
    """Test registration failure if get_name is missing."""
    with caplog.at_level(logging.ERROR):
        class ProcessorMissingGetName(BaseSystemPromptProcessor, metaclass=SystemPromptProcessorMeta):
            # Missing get_name
            def process(self, system_prompt: str, tool_instances: Dict[str, 'BaseTool'], agent_id: str) -> str:
                return system_prompt # pragma: no cover
    
    assert "ProcessorMissingGetName is missing required static/class method 'get_name'" in caplog.text
    # Check that it wasn't registered under its class name or any other name
    assert default_system_prompt_processor_registry.get_processor_definition("ProcessorMissingGetName") is None


def test_meta_handles_invalid_get_name_return(caplog):
    """Test registration failure if get_name returns non-string or empty string."""
    with caplog.at_level(logging.ERROR):
        class ProcessorInvalidGetNameReturn(BaseSystemPromptProcessor, metaclass=SystemPromptProcessorMeta):
            @classmethod
            def get_name(cls): # type: ignore
                return None # Invalid return type
            def process(self, system_prompt: str, tool_instances: Dict[str, 'BaseTool'], agent_id: str) -> str:
                return system_prompt # pragma: no cover
    
    assert "must return a valid string from static get_name()" in caplog.text
    assert default_system_prompt_processor_registry.get_processor_definition("ProcessorInvalidGetNameReturn") is None
    # What if get_name() itself raises an error?
    caplog.clear()
    with caplog.at_level(logging.ERROR):
        class ProcessorErrorInGetName(BaseSystemPromptProcessor, metaclass=SystemPromptProcessorMeta):
            @classmethod
            def get_name(cls) -> str:
                raise RuntimeError("Failure in get_name")
            def process(self, system_prompt: str, tool_instances: Dict[str, 'BaseTool'], agent_id: str) -> str:
                return system_prompt # pragma: no cover
    
    assert "Failed to auto-register system prompt processor class ProcessorErrorInGetName" in caplog.text
    assert "RuntimeError: Failure in get_name" in caplog.text


def test_meta_registration_with_custom_name():
    """Test auto-registration uses the name from get_name()."""
    class CustomNamedProcessor(BaseSystemPromptProcessor, metaclass=SystemPromptProcessorMeta):
        @classmethod
        def get_name(cls) -> str:
            return "MyUniqueProcessorName"
        def process(self, system_prompt: str, tool_instances: Dict[str, 'BaseTool'], agent_id: str) -> str:
            return system_prompt # pragma: no cover

    definition = default_system_prompt_processor_registry.get_processor_definition("MyUniqueProcessorName")
    assert definition is not None
    assert definition.processor_class == CustomNamedProcessor
    assert default_system_prompt_processor_registry.get_processor_definition("CustomNamedProcessor") is None

