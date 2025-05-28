import pytest
from typing import Dict, TYPE_CHECKING

from autobyteus.agent.system_prompt_processor.base_processor import BaseSystemPromptProcessor
from autobyteus.tools.base_tool import BaseTool

if TYPE_CHECKING:
    from autobyteus.agent.context import AgentContext # Added for type hint

class MyTestProcessor(BaseSystemPromptProcessor):
    """A concrete implementation for testing BaseSystemPromptProcessor."""
    # get_name() will use default implementation (class name)

    def process(self, system_prompt: str, tool_instances: Dict[str, 'BaseTool'], agent_id: str, context: 'AgentContext') -> str: # Added context
        # Simple implementation for testing purposes
        return f"{system_prompt} - Processed by {self.get_name()} for {agent_id} with tools: {list(tool_instances.keys())} using context def: {context.definition.name}"

class MyRenamedTestProcessor(BaseSystemPromptProcessor):
    @classmethod
    def get_name(cls) -> str:
        return "CustomProcessorName"

    def process(self, system_prompt: str, tool_instances: Dict[str, 'BaseTool'], agent_id: str, context: 'AgentContext') -> str: # Added context
        return system_prompt # pragma: no cover

def test_base_processor_get_name_default():
    """Test the default get_name() method of BaseSystemPromptProcessor."""
    assert MyTestProcessor.get_name() == "MyTestProcessor"

def test_base_processor_get_name_overridden():
    """Test get_name() when overridden in a subclass."""
    assert MyRenamedTestProcessor.get_name() == "CustomProcessorName"

def test_base_processor_process_abstract():
    """Ensure the base process method is abstract and raises NotImplementedError."""
    with pytest.raises(TypeError): 
        class IncompleteProcessor(BaseSystemPromptProcessor):
            # Missing process method or other abstract methods if any
            pass
    pass 

def test_base_processor_repr():
    """Test the __repr__ method."""
    processor_instance = MyTestProcessor()
    assert repr(processor_instance) == "<MyTestProcessor>"

    renamed_processor_instance = MyRenamedTestProcessor()
    assert repr(renamed_processor_instance) == "<MyRenamedTestProcessor>"

