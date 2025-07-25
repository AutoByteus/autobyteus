# file: autobyteus/autobyteus/agent/tool_execution_result_processor/__init__.py
"""
Components for processing tool execution results before they are sent to the LLM.
"""
from .base_processor import BaseToolExecutionResultProcessor

__all__ = [
    "BaseToolExecutionResultProcessor",
]
