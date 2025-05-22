# file: autobyteus/autobyteus/agent/input_processor/__init__.py
"""
Components for pre-processing AgentUserMessage objects, including auto-registration.
"""
from .processor_definition import AgentUserInputMessageProcessorDefinition
from .processor_registry import AgentUserInputMessageProcessorRegistry, default_input_processor_registry
from .processor_meta import AgentUserInputMessageProcessorMeta
from .base_user_input_processor import BaseAgentUserInputMessageProcessor

# Import processors from their individual files to ensure they are registered by the metaclass
from .passthrough_input_processor import PassthroughInputProcessor
from .metadata_appending_input_processor import MetadataAppendingInputProcessor
from .content_prefixing_input_processor import ContentPrefixingInputProcessor


__all__ = [
    "AgentUserInputMessageProcessorDefinition",
    "AgentUserInputMessageProcessorRegistry",
    "default_input_processor_registry",
    "AgentUserInputMessageProcessorMeta",
    "BaseAgentUserInputMessageProcessor",
    "PassthroughInputProcessor",
    "MetadataAppendingInputProcessor",
    "ContentPrefixingInputProcessor",
]
