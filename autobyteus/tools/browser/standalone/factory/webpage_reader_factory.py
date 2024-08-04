from autobyteus.tools.factory.tool_factory import ToolFactory
from autobyteus.tools.browser.standalone.webpage_reader import WebPageReader
from autobyteus.utils.html_cleaner import CleaningMode

class WebPageReaderFactory(ToolFactory):
    def __init__(self, cleaning_mode: CleaningMode = CleaningMode.THOROUGH):
        self.cleaning_mode = cleaning_mode

    def create_tool(self) -> WebPageReader:
        return WebPageReader(cleaning_mode=self.cleaning_mode)