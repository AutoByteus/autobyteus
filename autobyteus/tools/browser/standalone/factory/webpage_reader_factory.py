from autobyteus.tools.factory.tool_factory import ToolFactory
from autobyteus.tools.browser.standalone.webpage_reader import WebPageReader
from autobyteus.utils.html_cleaner import CleaningMode

class WebPageReaderFactory(ToolFactory):
    def __init__(self, content_cleanup_level: CleaningMode = CleaningMode.THOROUGH):
        self.content_cleanup_level = content_cleanup_level

    def create_tool(self) -> WebPageReader:
        return WebPageReader(content_cleanup_level=self.content_cleanup_level)