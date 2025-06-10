# file: autobyteus/autobyteus/agent/system_prompt_processor/__init__.py
"""
Components for pre-processing and enhancing agent system prompts.
"""
from .base_processor import BaseSystemPromptProcessor

# Import concrete processors here to make them easily accessible for instantiation
from .tool_description_injector_processor import ToolDescriptionInjectorProcessor
from .tool_usage_example_injector_processor import ToolUsageExampleInjectorProcessor

__all__ = [
    "BaseSystemPromptProcessor",
    "ToolDescriptionInjectorProcessor", 
    "ToolUsageExampleInjectorProcessor",
]
