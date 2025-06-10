# file: autobyteus/autobyteus/agent/input_processor/__init__.py
"""
Components for pre-processing AgentUserMessage objects.
"""
from .base_user_input_processor import BaseAgentUserInputMessageProcessor

# Import concrete processors to make them easily accessible for instantiation
from .passthrough_input_processor import PassthroughInputProcessor
from .metadata_appending_input_processor import MetadataAppendingInputProcessor
from .content_prefixing_input_processor import ContentPrefixingInputProcessor


__all__ = [
    "BaseAgentUserInputMessageProcessor",
    "PassthroughInputProcessor",
    "MetadataAppendingInputProcessor",
    "ContentPrefixingInputProcessor",
]
