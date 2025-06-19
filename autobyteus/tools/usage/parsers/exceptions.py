# file: autobyteus/autobyteus/tools/usage/parsers/exceptions.py
"""
Custom exceptions for the tool usage parsing module.
"""

class ToolUsageParseException(Exception):
    """
    Raised when a tool usage parser fails to parse an LLM response due to
    malformed content or other parsing errors.
    """
    def __init__(self, message: str, original_exception: Exception = None):
        super().__init__(message)
        self.original_exception = original_exception
