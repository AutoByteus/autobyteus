import pytest
from typing import Dict, TYPE_CHECKING

from autobyteus.agent.system_prompt_processor.base_processor import BaseSystemPromptProcessor
from autobyteus.agent.system_prompt_processor.processor_definition import SystemPromptProcessorDefinition

if TYPE_CHECKING:
    from autobyteus.agent.context import AgentContext
    from autobyteus.tools.base_tool import BaseTool

class DummySystemPromptProcessor(BaseSystemPromptProcessor):
    def process(self, system_prompt: str, tool_instances: Dict[str, 'BaseTool'], agent_id: str, context: 'AgentContext') -> str:
        return system_prompt # pragma: no cover

def test_processor_definition_valid_creation():
    """Test successful creation of SystemPromptProcessorDefinition."""
    definition = SystemPromptProcessorDefinition(name="TestProcessor", processor_class=DummySystemPromptProcessor)
    assert definition.name == "TestProcessor"
    assert definition.processor_class == DummySystemPromptProcessor

def test_processor_definition_invalid_name():
    """Test creation with invalid names."""
    with pytest.raises(ValueError, match="System Prompt Processor name must be a non-empty string."):
        SystemPromptProcessorDefinition(name="", processor_class=DummySystemPromptProcessor)
    
    with pytest.raises(ValueError, match="System Prompt Processor name must be a non-empty string."):
        SystemPromptProcessorDefinition(name=None, processor_class=DummySystemPromptProcessor) # type: ignore

def test_processor_definition_invalid_class():
    """Test creation with invalid processor_class."""
    class NotAProcessor:
        pass

    with pytest.raises(ValueError, match="processor_class must be a class type."):
        SystemPromptProcessorDefinition(name="TestProcessor", processor_class=NotAProcessor()) # type: ignore
    
    with pytest.raises(ValueError, match="processor_class must be a class type."):
        SystemPromptProcessorDefinition(name="TestProcessor", processor_class=None) # type: ignore


def test_processor_definition_repr():
    """Test the __repr__ method of SystemPromptProcessorDefinition."""
    definition = SystemPromptProcessorDefinition(name="MyProc", processor_class=DummySystemPromptProcessor)
    expected_repr = "<SystemPromptProcessorDefinition name='MyProc', class='DummySystemPromptProcessor'>"
    assert repr(definition) == expected_repr
