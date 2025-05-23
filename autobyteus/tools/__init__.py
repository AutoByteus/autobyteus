# file: autobyteus/autobyteus/tools/__init__.py
"""
This package provides the base classes, decorators, registries, and schema definitions
for creating and managing tools within the AutoByteUs framework.
It also contains implementations of various standard tools.
"""

# Core components for defining and registering tools
from .base_tool import BaseTool
from .functional_tool import tool # The @tool decorator
from .registry import default_tool_registry, ToolRegistry, ToolDefinition
from .parameter_schema import ParameterSchema, ParameterDefinition, ParameterType
from .tool_config import ToolConfig # Configuration data object, primarily for class-based tools

# --- Optional: Re-export specific tools for easier access ---
# Users can import tools directly, e.g., `from autobyteus.tools.bash_executor import bash_executor`
# or they can be re-exported here for `from autobyteus.tools import bash_executor`.
# For now, direct import from their modules is preferred to keep this __init__ clean.

# Example of how tools *could* be re-exported if desired:
# from .bash.bash_executor import bash_executor # Functional tool
# from .file.file_reader import file_reader     # Functional tool
# from .file.file_writer import file_writer     # Functional tool
# from .ask_user_input import ask_user_input    # Functional tool
# from .pdf_downloader import pdf_downloader    # Functional tool
# from .messaging.send_message_to import send_message_to # Functional tool

# Class-based tools (examples, if any were kept as directly exportable)
# from .image_downloader import ImageDownloader # Class-based tool
# from .timer import Timer                      # Class-based tool

# Exposing sub-packages might also be an option if they contain many tools:
# import autobyteus.tools.browser.standalone as standalone_browser_tools
# import autobyteus.tools.browser.session_aware as session_aware_browser_tools

__all__ = [
    # Core framework elements
    "BaseTool",
    "tool",  # The decorator for functional tools
    "ToolDefinition",
    "ToolRegistry",
    "default_tool_registry",
    "ParameterSchema",
    "ParameterDefinition",
    "ParameterType",
    "ToolConfig",

    # Specific tools are generally not added to __all__ here to avoid cluttering
    # the `from autobyteus.tools import *` namespace. Users should import them
    # from their specific modules (e.g., `from autobyteus.tools.bash.bash_executor import bash_executor`).
]
