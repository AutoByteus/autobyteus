# file: autobyteus/autobyteus/agent/input_processor/__init__.py
"""
Components for pre-processing AgentUserMessage objects.
"""
from .base_user_input_processor import BaseAgentUserInputMessageProcessor

# Concrete processors have been removed. Users can define their own.


__all__ = [
    "BaseAgentUserInputMessageProcessor",
]
