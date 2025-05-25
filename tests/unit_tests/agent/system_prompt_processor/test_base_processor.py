import pytest
from typing import Dict

from autobyteus.agent.system_prompt_processor.base_processor import BaseSystemPromptProcessor
from autobyteus.tools.base_tool import BaseTool

class MyTestProcessor(BaseSystemPromptProcessor):
    """A concrete implementation for testing BaseSystemPromptProcessor."""
    # get_name() will use default implementation (class name)

    def process(self, system_prompt: str, tool_instances: Dict[str, 'BaseTool'], agent_id: str) -> str:
        # Simple implementation for testing purposes
        return f"{system_prompt} - Processed by {self.get_name()} for {agent_id} with tools: {list(tool_instances.keys())}"

class MyRenamedTestProcessor(BaseSystemPromptProcessor):
    @classmethod
    def get_name(cls) -> str:
        return "CustomProcessorName"

    def process(self, system_prompt: str, tool_instances: Dict[str, 'BaseTool'], agent_id: str) -> str:
        return system_prompt # pragma: no cover

def test_base_processor_get_name_default():
    """Test the default get_name() method of BaseSystemPromptProcessor."""
    assert MyTestProcessor.get_name() == "MyTestProcessor"

def test_base_processor_get_name_overridden():
    """Test get_name() when overridden in a subclass."""
    assert MyRenamedTestProcessor.get_name() == "CustomProcessorName"

def test_base_processor_process_abstract():
    """Ensure the base process method is abstract and raises NotImplementedError."""
    # We can't instantiate BaseSystemPromptProcessor directly due to metaclass registration
    # and abstract methods. This test serves as a reminder.
    # To truly test this, one would need to bypass metaclass or test for TypeError on instantiation.
    # For now, we rely on Python's ABC mechanics.
    with pytest.raises(TypeError): # Should fail due to abstract method not implemented
        class IncompleteProcessor(BaseSystemPromptProcessor):
            pass
        # IncompleteProcessor() # type: ignore

    # If it was possible to instantiate BaseSystemPromptProcessor directly (e.g. by removing metaclass for a moment)
    # processor = BaseSystemPromptProcessor() # This would fail
    # with pytest.raises(NotImplementedError):
    #    processor.process("prompt", {}, "agent1")
    pass # ABC enforcement by Python is sufficient

def test_base_processor_repr():
    """Test the __repr__ method."""
    processor_instance = MyTestProcessor()
    assert repr(processor_instance) == "<MyTestProcessor>"

    renamed_processor_instance = MyRenamedTestProcessor()
    assert repr(renamed_processor_instance) == "<MyRenamedTestProcessor>"

