# file: autobyteus/autobyteus/agent/system_prompt_processor/__init__.py
"""
Components for pre-processing and enhancing agent system prompts.
This includes base classes for processors, their definitions, metaclasses for
auto-registration, and the central registry.
"""
from .processor_definition import SystemPromptProcessorDefinition
from .processor_registry import SystemPromptProcessorRegistry, default_system_prompt_processor_registry
from .processor_meta import SystemPromptProcessorMeta
from .base_processor import BaseSystemPromptProcessor

# Import concrete processors here to ensure they are registered by the metaclass
from .tool_description_injector_processor import ToolDescriptionInjectorProcessor
from .tool_usage_example_injector_processor import ToolUsageExampleInjectorProcessor # Added new processor

__all__ = [
    "SystemPromptProcessorDefinition",
    "SystemPromptProcessorRegistry",
    "default_system_prompt_processor_registry",
    "SystemPromptProcessorMeta",
    "BaseSystemPromptProcessor",
    "ToolDescriptionInjectorProcessor", 
    "ToolUsageExampleInjectorProcessor", # Added new processor to __all__
]
