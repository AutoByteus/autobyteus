# file: autobyteus/autobyteus/tools/__init__.py
"""
This package provides the base classes, decorators, and schema definitions
for creating tools within the AutoByteUs framework.
It also contains implementations of various standard tools.
"""

# Core components for defining tools
from .base_tool import BaseTool
from .functional_tool import tool # The @tool decorator
from .parameter_schema import ParameterSchema, ParameterDefinition, ParameterType
from .tool_config import ToolConfig # Configuration data object, primarily for class-based tools
from .tool_category import ToolCategory

# --- Re-export specific tools for easier access ---

# Functional tools (decorated functions are now instances)
from .ask_user_input import ask_user_input
from .pdf_downloader import pdf_downloader
from .bash.bash_executor import bash_executor
from .file.file_reader import file_reader
from .file.file_writer import file_writer

# General Class-based tools
from .image_downloader import ImageDownloader
from .timer import Timer

# Standalone Browser tools
from .browser.standalone.google_search_ui import GoogleSearch
from .browser.standalone.navigate_to import NavigateTo as StandaloneNavigateTo # Alias to avoid name clash
from .browser.standalone.webpage_reader import WebPageReader as StandaloneWebPageReader # Alias
from .browser.standalone.webpage_screenshot_taker import WebPageScreenshotTaker as StandaloneWebPageScreenshotTaker # Alias
from .browser.standalone.webpage_image_downloader import WebPageImageDownloader
from .browser.standalone.web_page_pdf_generator import WebPagePDFGenerator

# Session-Aware Browser tools
from .browser.session_aware.browser_session_aware_navigate_to import BrowserSessionAwareNavigateTo
from .browser.session_aware.browser_session_aware_web_element_trigger import BrowserSessionAwareWebElementTrigger
from .browser.session_aware.browser_session_aware_webpage_reader import BrowserSessionAwareWebPageReader
from .browser.session_aware.browser_session_aware_webpage_screenshot_taker import BrowserSessionAwareWebPageScreenshotTaker


__all__ = [
    # Core framework elements
    "BaseTool",
    "tool",  # The decorator for functional tools
    "ParameterSchema",
    "ParameterDefinition",
    "ParameterType",
    "ToolConfig",
    "ToolCategory",

    # Re-exported functional tool instances
    "ask_user_input",
    "pdf_downloader",
    "bash_executor",
    "file_reader",
    "file_writer",

    # Re-exported general class-based tools
    "ImageDownloader",
    "Timer",

    # Re-exported Standalone Browser tools
    "GoogleSearch",
    "StandaloneNavigateTo",
    "StandaloneWebPageReader",
    "StandaloneWebPageScreenshotTaker",
    "WebPageImageDownloader",
    "WebPagePDFGenerator",

    # Re-exported Session-Aware Browser tools
    "BrowserSessionAwareNavigateTo",
    "BrowserSessionAwareWebElementTrigger",
    "BrowserSessionAwareWebPageReader",
    "BrowserSessionAwareWebPageScreenshotTaker",
]
