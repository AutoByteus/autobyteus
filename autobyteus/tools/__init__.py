# file: autobyteus/autobyteus/tools/__init__.py
"""
This package provides the base classes, decorators, and schema definitions
for creating tools within the AutoByteUs framework.
It also contains implementations of various standard tools.
"""

import logging

# Core components for defining tools
from .base_tool import BaseTool
from .functional_tool import tool # The @tool decorator
from autobyteus.utils.parameter_schema import ParameterSchema, ParameterDefinition, ParameterType
from .tool_config import ToolConfig # Configuration data object, primarily for class-based tools
from .tool_origin import ToolOrigin
from .tool_category import ToolCategory

logger = logging.getLogger(__name__)

# --- Re-export specific tools for easier access ---

# Functional tools (decorated functions are now instances)
from .bash.bash_executor import bash_executor
from .file.read_file import read_file
from .file.write_file import write_file
from .file.edit_file import edit_file
from .file.search_files import search_files
from .file.list_directory import list_directory

# General Class-based tools
try:
    from .search_tool import Search
except ModuleNotFoundError as import_err:
    logger.warning("Search tool not available: %s", import_err)
    Search = None
from .timer import Timer
try:
    from .multimedia.image_tools import GenerateImageTool, EditImageTool
except ModuleNotFoundError as import_err:
    logger.warning("Image tools not available: %s", import_err)
    GenerateImageTool = None
    EditImageTool = None
try:
    from .multimedia.media_reader_tool import ReadMediaFile
except ModuleNotFoundError as import_err:
    logger.warning("Media reader tool not available: %s", import_err)
    ReadMediaFile = None
try:
    from autobyteus.multimedia.download_media_tool import DownloadMediaTool
except ModuleNotFoundError as import_err:
    logger.warning("Download media tool not available: %s", import_err)
    DownloadMediaTool = None

# Standalone Browser tools
try:
    from .browser.standalone.navigate_to import NavigateTo as StandaloneNavigateTo # Alias to avoid name clash
    from .browser.standalone.webpage_reader import WebPageReader as StandaloneWebPageReader # Alias
    from .browser.standalone.webpage_screenshot_taker import WebPageScreenshotTaker as StandaloneWebPageScreenshotTaker # Alias
    from .browser.standalone.webpage_image_downloader import WebPageImageDownloader
    from .browser.standalone.web_page_pdf_generator import WebPagePDFGenerator
except ModuleNotFoundError as import_err:
    logger.warning('Standalone browser tools not available: %s', import_err)
    StandaloneNavigateTo = None
    StandaloneWebPageReader = None
    StandaloneWebPageScreenshotTaker = None
    WebPageImageDownloader = None
    WebPagePDFGenerator = None

# Session-Aware Browser tools
try:
    from .browser.session_aware.browser_session_aware_navigate_to import BrowserSessionAwareNavigateTo
    from .browser.session_aware.browser_session_aware_web_element_trigger import BrowserSessionAwareWebElementTrigger
    from .browser.session_aware.browser_session_aware_webpage_reader import BrowserSessionAwareWebPageReader
    from .browser.session_aware.browser_session_aware_webpage_screenshot_taker import BrowserSessionAwareWebPageScreenshotTaker
except ModuleNotFoundError as import_err:
    logger.warning('Session-aware browser tools not available: %s', import_err)
    BrowserSessionAwareNavigateTo = None
    BrowserSessionAwareWebElementTrigger = None
    BrowserSessionAwareWebPageReader = None
    BrowserSessionAwareWebPageScreenshotTaker = None


__all__ = [
    # Core framework elements
    "BaseTool",
    "tool",  # The decorator for functional tools
    "ParameterSchema",
    "ParameterDefinition",
    "ParameterType",
    "ToolConfig",
    "ToolOrigin",
    "ToolCategory",

    # Re-exported functional tool instances
    "bash_executor",
    "read_file",
    "write_file",
    "edit_file",
    "search_files",
    "list_directory",

    # Re-exported general class-based tools
    "Search",
    "Timer",
    "GenerateImageTool",
    "EditImageTool",
    "ReadMediaFile",
    "DownloadMediaTool",

    # Re-exported Standalone Browser tools
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
