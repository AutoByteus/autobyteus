# file: autobyteus/autobyteus/tools/tool_state.py
"""
Defines the ToolState class, an explicit container for a tool's internal state,
providing a dictionary-like interface for backward compatibility.
"""
from collections import UserDict

class ToolState(UserDict):
    """
    A specialized container for a tool's state.

    This class inherits from collections.UserDict to provide a dictionary-like
    interface, ensuring that existing tools can interact with the state attribute
    (tool.tool_state) just as they would with a regular dictionary.

    The primary purpose of this class is to make the concept of a tool's
    state explicit in the framework's type system, improving code clarity
    and developer experience.
    """
    pass
