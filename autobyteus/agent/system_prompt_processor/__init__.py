# file: autobyteus/autobyteus/agent/system_prompt_processor/__init__.py
"""
Components for pre-processing and enhancing agent system prompts.
"""
from .base_processor import BaseSystemPromptProcessor

# Import concrete processors here to make them easily accessible for instantiation
from .tool_manifest_injector_processor import ToolManifestInjectorProcessor


__all__ = [
    "BaseSystemPromptProcessor",
    "ToolManifestInjectorProcessor",
]
